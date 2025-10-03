# -*- coding: utf-8 -*-
"""
Serviço de agendamento para automação de recibos de IA.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from database import SessionLocal
from models.receipt_models import ReceiptJob, Recibo, JobStatus
from services.llm_service import LLMService
from services.receipt_processor import ReceiptProcessor
from services.gmail_service import GmailService
from services.email_service import EmailService
from config import config


class SchedulerService:
    """Serviço de agendamento para automação de recibos."""
    
    def __init__(self, gmail_service: Optional[GmailService] = None):
        """
        Inicializa o serviço de agendamento.
        
        Args:
            gmail_service: Serviço Gmail (opcional)
        """
        self.scheduler = BackgroundScheduler()
        self.gmail_service = gmail_service
        self.llm_service = LLMService()
        self.receipt_processor = ReceiptProcessor(self.llm_service)
        self.email_service = EmailService()
        self.logger = self._setup_logger()
        
        # Configurar listeners de eventos
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)
        
        # Adicionar jobs
        self._add_jobs()
    
    def _setup_logger(self) -> logging.Logger:
        """Configura o logger para o scheduler."""
        logger = logging.getLogger('scheduler_service')
        logger.setLevel(logging.INFO)
        
        # Criar handler para arquivo
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, 'scheduler.log'),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    def _add_jobs(self):
        """Adiciona todos os jobs agendados."""
        try:
            # Job 1: Coleta Gmail (dias 15-18 do mês, 3x por dia)
            self.scheduler.add_job(
                func=self._collect_gmail_receipts,
                trigger=CronTrigger(
                    day='15-18',
                    hour='9,14,19',
                    minute=0
                ),
                id='collect_gmail_receipts',
                name='Coleta Gmail - Recibos de IA',
                replace_existing=True
            )
            
            # Job 2: Coleta APIs (diário às 8h)
            self.scheduler.add_job(
                func=self._collect_api_receipts,
                trigger=CronTrigger(hour=8, minute=0),
                id='collect_api_receipts',
                name='Coleta APIs - Recibos de IA',
                replace_existing=True
            )
            
            # Job 3: Processamento de jobs pendentes (a cada 2 horas)
            self.scheduler.add_job(
                func=self._process_pending_jobs,
                trigger=IntervalTrigger(hours=2),
                id='process_pending_jobs',
                name='Processar Jobs Pendentes',
                replace_existing=True
            )
            
            # Job 4: Relatório mensal (dia 1 às 9h)
            self.scheduler.add_job(
                func=self._generate_monthly_report,
                trigger=CronTrigger(day=1, hour=9, minute=0),
                id='monthly_report',
                name='Relatório Mensal de Recibos',
                replace_existing=True
            )
            
            # Job 5: Manutenção e limpeza (domingos às 2h)
            self.scheduler.add_job(
                func=self._maintenance_cleanup,
                trigger=CronTrigger(day_of_week=6, hour=2, minute=0),
                id='maintenance_cleanup',
                name='Manutenção e Limpeza',
                replace_existing=True
            )
            
            self.logger.info("✅ Jobs agendados configurados com sucesso")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao configurar jobs: {str(e)}")
    
    def start(self):
        """Inicia o scheduler."""
        try:
            if not self.scheduler.running:
                self.scheduler.start()
                self.logger.info("🚀 Scheduler iniciado com sucesso")
            else:
                self.logger.warning("⚠️ Scheduler já está rodando")
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar scheduler: {str(e)}")
    
    def stop(self):
        """Para o scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("🛑 Scheduler parado com sucesso")
            else:
                self.logger.warning("⚠️ Scheduler já estava parado")
        except Exception as e:
            self.logger.error(f"❌ Erro ao parar scheduler: {str(e)}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retorna status do scheduler.
        
        Returns:
            Dicionário com status e informações
        """
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if hasattr(job, 'next_run_time') and job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {
            "running": self.scheduler.running,
            "jobs_count": len(jobs),
            "jobs": jobs,
            "timezone": str(self.scheduler.timezone)
        }
    
    def _collect_gmail_receipts(self):
        """Coleta recibos do Gmail."""
        self.logger.info("📧 Iniciando coleta de recibos do Gmail")
        
        if not self.gmail_service:
            self.logger.warning("⚠️ Gmail service não configurado")
            return
        
        try:
            session = SessionLocal()
            created_count = 0
            errors = []
            
            # Lista de usuários para coletar
            users = [config.GMAIL_DELEGATED_USER] if config.GMAIL_DELEGATED_USER else []
            
            for user in users:
                try:
                    # Buscar mensagens de recibos
                    messages = self.gmail_service.list_gemini_messages(user, max_results=50)
                    
                    for msg in messages:
                        msg_id = msg['id']
                        
                        # Verificar se já existe
                        existing = session.query(ReceiptJob).filter_by(
                            source_hash=msg_id
                        ).first()
                        
                        if existing:
                            continue
                        
                        # Obter detalhes da mensagem
                        full_msg = self.gmail_service.get_message(user, msg_id)
                        text = self.gmail_service.extract_plain_text(full_msg)
                        
                        # Criar job
                        job = ReceiptJob(
                            source_uri=f"gmail://{user}/{msg_id}",
                            source_hash=msg_id,
                            status=JobStatus.DISCOVERED,
                            attempts=0,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            collaborator_email=user
                        )
                        
                        session.add(job)
                        created_count += 1
                    
                    session.commit()
                    self.logger.info(f"✅ Coletados {created_count} recibos do usuário {user}")
                    
                except Exception as e:
                    errors.append(f"Usuário {user}: {str(e)}")
                    self.logger.error(f"❌ Erro ao coletar de {user}: {str(e)}")
            
            session.close()
            
            # Enviar notificação se houver novos recibos
            if created_count > 0:
                self._send_new_receipts_notification(created_count)
            
            if errors:
                self.logger.warning(f"⚠️ Erros na coleta: {errors}")
                
        except Exception as e:
            self.logger.error(f"❌ Erro geral na coleta Gmail: {str(e)}")
    
    def _collect_api_receipts(self):
        """Coleta recibos de APIs externas."""
        self.logger.info("🔌 Iniciando coleta de recibos de APIs")
        
        try:
            # Aqui você pode implementar coleta de APIs específicas
            # Por exemplo: OpenAI API, Anthropic API, etc.
            
            # Por enquanto, apenas log
            self.logger.info("✅ Coleta de APIs concluída (implementação futura)")
            
        except Exception as e:
            self.logger.error(f"❌ Erro na coleta de APIs: {str(e)}")
    
    def _process_pending_jobs(self):
        """Processa jobs pendentes."""
        self.logger.info("⚙️ Iniciando processamento de jobs pendentes")
        
        try:
            session = SessionLocal()
            
            # Buscar jobs pendentes
            pending_jobs = session.query(ReceiptJob).filter(
                ReceiptJob.status == JobStatus.DISCOVERED
            ).limit(10).all()
            
            processed_count = 0
            
            for job in pending_jobs:
                try:
                    # Atualizar status para processando
                    job.status = JobStatus.PROCESSING
                    job.attempts = (job.attempts or 0) + 1
                    job.updated_at = datetime.utcnow()
                    session.commit()
                    
                    # Processar recibo
                    result = self._process_single_job(job)
                    
                    if result['success']:
                        job.status = JobStatus.PROCESSED
                        processed_count += 1
                        self.logger.info(f"✅ Job {job.id} processado com sucesso")
                    else:
                        job.status = JobStatus.FAILED
                        self.logger.error(f"❌ Job {job.id} falhou: {result.get('error')}")
                    
                    job.updated_at = datetime.utcnow()
                    session.commit()
                    
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.updated_at = datetime.utcnow()
                    session.commit()
                    self.logger.error(f"❌ Erro ao processar job {job.id}: {str(e)}")
            
            session.close()
            
            if processed_count > 0:
                self.logger.info(f"✅ Processados {processed_count} jobs")
            
        except Exception as e:
            self.logger.error(f"❌ Erro no processamento de jobs: {str(e)}")
    
    def _process_single_job(self, job: ReceiptJob) -> Dict[str, Any]:
        """
        Processa um job individual.
        
        Args:
            job: Job a ser processado
            
        Returns:
            Dicionário com resultado
        """
        try:
            # Extrair texto baseado no tipo de fonte
            if job.source_uri.startswith('gmail://'):
                # Processar email do Gmail
                if not self.gmail_service:
                    return {"success": False, "error": "Gmail service não disponível"}
                
                # Extrair user e msg_id do URI
                parts = job.source_uri.replace('gmail://', '').split('/')
                if len(parts) != 2:
                    return {"success": False, "error": "URI Gmail inválida"}
                
                user, msg_id = parts
                full_msg = self.gmail_service.get_message(user, msg_id)
                text = self.gmail_service.extract_plain_text(full_msg)
                
            else:
                # Processar arquivo local
                if not os.path.exists(job.source_uri):
                    return {"success": False, "error": "Arquivo não encontrado"}
                
                from services.file_service import FileService
                file_service = FileService()
                text_result = file_service.extract_text_from_file(job.source_uri)
                
                if not text_result['success']:
                    return {"success": False, "error": text_result['error']}
                
                text = text_result['text']
            
            # Processar com ReceiptProcessor
            result = self.receipt_processor.extract_receipt_data(text, provider='auto')
            
            if result['success']:
                # Salvar dados extraídos
                self._save_extracted_data(job, result['extracted_data'])
                return {"success": True, "data": result['extracted_data']}
            else:
                return {"success": False, "error": result.get('error', 'Erro desconhecido')}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_extracted_data(self, job: ReceiptJob, data: Dict[str, Any]):
        """
        Salva dados extraídos no banco.
        
        Args:
            job: Job processado
            data: Dados extraídos
        """
        try:
            session = SessionLocal()
            
            # Criar registro de recibo
            recibo = Recibo(
                job_id=job.id,
                provider=data.get('provider'),
                amount=data.get('amount'),
                currency=data.get('currency'),
                date=data.get('date'),
                description=data.get('description'),
                invoice_number=data.get('invoice_number'),
                vendor=data.get('vendor'),
                confidence_score=data.get('confidence_score'),
                raw_data=json.dumps(data),
                created_at=datetime.utcnow()
            )
            
            session.add(recibo)
            session.commit()
            session.close()
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar dados extraídos: {str(e)}")
    
    def _generate_monthly_report(self):
        """Gera relatório mensal."""
        self.logger.info("📊 Iniciando geração de relatório mensal")
        
        try:
            session = SessionLocal()
            
            # Calcular período (mês anterior)
            now = datetime.utcnow()
            first_day = now.replace(day=1) - timedelta(days=1)
            first_day = first_day.replace(day=1)
            last_day = now.replace(day=1) - timedelta(days=1)
            
            # Buscar recibos do período
            recibos = session.query(Recibo).filter(
                Recibo.created_at >= first_day,
                Recibo.created_at <= last_day
            ).all()
            
            # Gerar estatísticas
            total_amount = sum(r.amount or 0 for r in recibos)
            total_count = len(recibos)
            
            # Agrupar por provedor
            providers = {}
            for recibo in recibos:
                provider = recibo.provider or 'Desconhecido'
                if provider not in providers:
                    providers[provider] = {'count': 0, 'amount': 0}
                providers[provider]['count'] += 1
                providers[provider]['amount'] += recibo.amount or 0
            
            # Enviar relatório por email
            self._send_monthly_report_email({
                'period': f"{first_day.strftime('%Y-%m-%d')} a {last_day.strftime('%Y-%m-%d')}",
                'total_count': total_count,
                'total_amount': total_amount,
                'providers': providers
            })
            
            session.close()
            self.logger.info("✅ Relatório mensal gerado e enviado")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao gerar relatório mensal: {str(e)}")
    
    def _maintenance_cleanup(self):
        """Executa manutenção e limpeza."""
        self.logger.info("🧹 Iniciando manutenção e limpeza")
        
        try:
            session = SessionLocal()
            
            # Limpar jobs antigos falhados (mais de 30 dias)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            old_failed_jobs = session.query(ReceiptJob).filter(
                ReceiptJob.status == JobStatus.FAILED,
                ReceiptJob.updated_at < cutoff_date
            ).all()
            
            for job in old_failed_jobs:
                session.delete(job)
            
            session.commit()
            
            # Limpar arquivos temporários
            temp_dir = 'uploads'
            if os.path.exists(temp_dir):
                for filename in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_age < cutoff_date:
                            try:
                                os.remove(file_path)
                            except:
                                pass
            
            session.close()
            self.logger.info(f"✅ Manutenção concluída - {len(old_failed_jobs)} jobs antigos removidos")
            
        except Exception as e:
            self.logger.error(f"❌ Erro na manutenção: {str(e)}")
    
    def _send_new_receipts_notification(self, count: int):
        """Envia notificação de novos recibos."""
        try:
            subject = f"💰 {count} Novos Recibos de IA Processados"
            body = f"""
            <h2>Novos Recibos Processados</h2>
            <p>O sistema processou automaticamente <strong>{count}</strong> novos recibos de IA.</p>
            <p>Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p>Acesse o sistema para visualizar os detalhes.</p>
            """
            
            self.email_service.send_email(
                to_emails=['contasapagar@zello.tec.br'],
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar notificação: {str(e)}")
    
    def _send_monthly_report_email(self, stats: Dict[str, Any]):
        """Envia relatório mensal por email."""
        try:
            subject = f"📊 Relatório Mensal de Recibos de IA - {stats['period']}"
            
            # Gerar HTML do relatório
            providers_html = ""
            for provider, data in stats['providers'].items():
                providers_html += f"""
                <tr>
                    <td>{provider}</td>
                    <td>{data['count']}</td>
                    <td>R$ {data['amount']:,.2f}</td>
                </tr>
                """
            
            body = f"""
            <h2>Relatório Mensal de Recibos de IA</h2>
            <p><strong>Período:</strong> {stats['period']}</p>
            
            <h3>Resumo Geral</h3>
            <ul>
                <li><strong>Total de Recibos:</strong> {stats['total_count']}</li>
                <li><strong>Valor Total:</strong> R$ {stats['total_amount']:,.2f}</li>
            </ul>
            
            <h3>Por Provedor</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr>
                    <th>Provedor</th>
                    <th>Quantidade</th>
                    <th>Valor Total</th>
                </tr>
                {providers_html}
            </table>
            
            <p>Relatório gerado automaticamente pelo Sistema de Automação de Recibos de IA</p>
            """
            
            self.email_service.send_email(
                to_emails=['contasapagar@zello.tec.br'],
                subject=subject,
                body=body,
                is_html=True
            )
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar relatório mensal: {str(e)}")
    
    def _job_executed(self, event):
        """Callback para job executado com sucesso."""
        self.logger.info(f"✅ Job executado: {event.job_id}")
    
    def _job_error(self, event):
        """Callback para erro em job."""
        self.logger.error(f"❌ Erro no job {event.job_id}: {event.exception}")
    
    def trigger_job(self, job_id: str) -> Dict[str, Any]:
        """
        Dispara um job manualmente.
        
        Args:
            job_id: ID do job
            
        Returns:
            Dicionário com resultado
        """
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return {"success": False, "error": "Job não encontrado"}
            
            # Executar job
            job.func()
            return {"success": True, "message": f"Job {job_id} executado com sucesso"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_job_logs(self, job_id: str, lines: int = 50) -> List[str]:
        """
        Obtém logs de um job específico.
        
        Args:
            job_id: ID do job
            lines: Número de linhas
            
        Returns:
            Lista de linhas de log
        """
        try:
            log_file = os.path.join('logs', 'scheduler.log')
            if not os.path.exists(log_file):
                return []
            
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
            
            # Filtrar linhas do job específico
            job_lines = [line for line in all_lines if job_id in line]
            return job_lines[-lines:] if job_lines else []
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao obter logs: {str(e)}")
            return []
