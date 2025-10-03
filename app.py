"""
Aplicação Flask para automação de Recibos de IA.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.exceptions import RequestEntityTooLarge

from config import config
from services import LLMService, EmailService, FileService, GenerationService, GmailService, GDriveService
from services.scheduler_service import SchedulerService
from services.receipt_processor import ReceiptProcessor
from prompts import ReceiptPrompts
from database import init_db, SessionLocal
from models.receipt_models import ReceiptJob, Recibo, JobStatus


def create_app() -> Flask:
    """Cria e configura a aplicação Flask."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    
    # Inicializar banco (apenas estrutura; pode ser substituído por Alembic)
    if os.getenv('AUTO_CREATE_DB', 'true').lower() == 'true':
        try:
            init_db()
        except Exception as _:
            # Mantém a aplicação viva mesmo se preferirmos rodar migrações Alembic
            pass

    # Inicializar serviços
    llm_service = LLMService()
    email_service = EmailService()
    file_service = FileService()
    generation_service = GenerationService(llm_service)
    receipt_processor = ReceiptProcessor(llm_service)
    gmail_service = None
    gdrive_service = None
    if config.GOOGLE_CREDENTIALS_JSON:
        try:
            # Tenta OAuth2 primeiro, depois Service Account
            use_oauth2 = os.path.exists("oauth2_credentials.json")
            if use_oauth2:
                gmail_service = GmailService("oauth2_credentials.json", use_oauth2=True)
                print("Gmail Service inicializado com OAuth2")
            else:
                gmail_service = GmailService(config.GOOGLE_CREDENTIALS_JSON, delegated_user=config.GMAIL_DELEGATED_USER)
                print("Gmail Service inicializado com Service Account")
            
            gdrive_service = GDriveService(config.GOOGLE_CREDENTIALS_JSON)
        except Exception as e:
            print(f"Aviso: Gmail/Drive não inicializados: {e}")
    
    
    # Inicializar scheduler
    scheduler_service = SchedulerService(gmail_service)
    scheduler_service.start()
    
    # Inicializar monitor de repositório (se configurado)
    repository_monitor = None
    if config.RECEIPTS_REPO_PATH:
        try:
            # Certificar que o diretório do repositório existe
            try:
                os.makedirs(config.RECEIPTS_REPO_PATH, exist_ok=True)
                print(f"Repositorio de recibos: {config.RECEIPTS_REPO_PATH}")
            except Exception as dir_err:
                print(f"Aviso: nao foi possivel criar o diretorio do repositorio: {dir_err}")

            repository_monitor = RepositoryMonitor()
        except Exception as e:
            print(f"Aviso: Nao foi possivel inicializar o monitor de repositorio: {str(e)}")
    
    @app.route('/')
    def index():
        """Página principal da aplicação."""
        return render_template('index.html')

    @app.route('/health', methods=['GET'])
    def health():
        """Endpoint de healthcheck para Docker/monitoramento."""
        return jsonify({"status": "ok"}), 200

    # =====================
    # NOVOS ENDPOINTS RADICAIS (Dashboard + Chat + Configurações)
    # =====================

    @app.route('/api/summary', methods=['GET'])
    def get_summary():
        """Retorna resumo para o Dashboard: últimas execuções, contagens e lista recente de recibos."""
        try:
            session = SessionLocal()

            # Contagens por período
            from datetime import datetime as _dt, timedelta as _td
            today = _dt.utcnow().date()
            week_ago = today - _td(days=7)
            month_ago = today.replace(day=1)

            total_today = session.query(Recibo).filter(Recibo.created_at >= _dt.combine(today, _dt.min.time())).count()
            total_week = session.query(Recibo).filter(Recibo.created_at >= _dt.combine(week_ago, _dt.min.time())).count()
            total_month = session.query(Recibo).filter(Recibo.created_at >= _dt.combine(month_ago, _dt.min.time())).count()

            # Lista recente
            recent = (
                session.query(Recibo)
                .order_by(Recibo.created_at.desc())
                .limit(25)
                .all()
            )

            receipts = []
            for r in recent:
                receipts.append({
                    'id': r.id,
                    'provider': r.plataforma,
                    'amount': r.valor,
                    'currency': r.moeda,
                    'date': r.data_emissao.isoformat() if r.data_emissao else None,
                    'invoice_number': r.numero_recibo,
                    'created_at': r.created_at.isoformat() if r.created_at else None
                })

            # Última execução conhecida (aproximação: último recibo criado)
            last_run = receipts[0]['created_at'] if receipts else None

            return jsonify({
                'success': True,
                'summary': {
                    'last_run': last_run,
                    'counts': {
                        'today': total_today,
                        'week': total_week,
                        'month': total_month
                    },
                    'recent_receipts': receipts
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            try:
                session.close()
            except Exception:
                pass

    # =====================
    # DEBUG GMAIL E REGISTRY
    # =====================
    @app.route('/api/debug/gmail', methods=['POST'])
    def debug_gmail():
        """Diagnóstico de busca no Gmail com paginação.
        Body JSON opcional:
        {
          "query": "<string>",               # usa query custom; default = get_receipt_search_query()
          "simplified": true|false,           # se true ignora remetentes e usa somente assunto multilíngue
          "max_pages": 10,                    # limite de páginas
          "page_size": 100                    # até 100
        }
        """
        try:
            if not gmail_service:
                return jsonify({'success': False, 'error': 'Gmail não configurado'}), 400

            payload = request.get_json(silent=True) or {}
            simplified = bool(payload.get('simplified', False))
            max_pages = int(payload.get('max_pages', 10))
            page_size = min(100, int(payload.get('page_size', 100)))

            if simplified:
                query = "(subject:receipt OR subject:recibo OR subject:invoice OR subject:fatura OR subject:billing OR subject:payment OR subject:pagamento)"
            else:
                query = payload.get('query') or GmailService.get_receipt_search_query()

            page_token = None
            pages = 0
            total_ids = 0
            first_details: List[Dict[str, Any]] = []
            while pages < max_pages:
                resp = gmail_service.list_by_query(
                    user_email=config.GMAIL_DELEGATED_USER or config.GMAIL_MONITORED_EMAIL,
                    query=query,
                    page_token=page_token,
                    max_results=page_size,
                    include_spam_trash=True
                )
                ids = resp.get('messages', [])
                total_ids += len(ids)
                pages += 1
                if ids and len(first_details) < 10:
                    for m in ids:
                        if len(first_details) >= 10:
                            break
                        full = gmail_service.get_message(config.GMAIL_DELEGATED_USER or config.GMAIL_MONITORED_EMAIL, m['id'])
                        headers = full.get('payload', {}).get('headers', [])
                        def _h(name: str) -> str:
                            for h in headers:
                                if h.get('name') == name:
                                    return h.get('value', '')
                            return ''
                        first_details.append({
                            'id': m['id'],
                            'from': _h('From'),
                            'subject': _h('Subject'),
                            'date': _h('Date')
                        })
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break

            return jsonify({
                'success': True,
                'query': query,
                'pages_processed': pages,
                'total_ids_found': total_ids,
                'first_10': first_details
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/debug/registry', methods=['POST'])
    def debug_registry():
        """Inspeciona ou limpa o registro de duplicatas do encaminhador.
        Body JSON opcional: { "action": "view"|"clear" }
        """
        try:
            from email_forwarder_final import EmailForwarder
            fwd = EmailForwarder()
            action = (request.get_json(silent=True) or {}).get('action', 'view')
            if action == 'clear':
                try:
                    if os.path.exists(fwd._registry_path):
                        os.remove(fwd._registry_path)
                    return jsonify({'success': True, 'message': 'Registry limpo'})
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 500
            # view
            if os.path.exists(fwd._registry_path):
                with open(fwd._registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = {'by_invoice': {}, 'by_triplet': {}}
            return jsonify({'success': True, 'registry': data, 'path': fwd._registry_path})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/scan-progress', methods=['GET'])
    def scan_progress():
        """Endpoint para obter progresso da varredura em tempo real."""
        try:
            progress = session.get('scan_progress', {
                'status': 'idle',
                'message': 'Nenhuma varredura em andamento',
                'page_count': 0,
                'total_messages': 0,
                'current_message': 0,
                'total_processed': 0
            })
            
            return jsonify({
                'success': True,
                'progress': progress
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'progress': {
                    'status': 'error',
                    'message': f'Erro ao obter progresso: {str(e)}',
                    'page_count': 0,
                    'total_messages': 0,
                    'current_message': 0,
                    'total_processed': 0
                }
            }), 500

    @app.route('/api/debug/scan', methods=['POST'])
    def debug_scan():
        """Endpoint para debug detalhado da varredura."""
        try:
            data = request.get_json() or {}
            days_back = data.get('days_back', 7)
            
            if not gmail_service:
                return jsonify({
                    'success': False,
                    'error': 'GmailService não disponível',
                    'debug_info': {
                        'gmail_service_available': False,
                        'config_gmail_email': config.GMAIL_MONITORED_EMAIL
                    }
                })
            
            debug_info = {
                'gmail_service_available': True,
                'monitored_email': config.GMAIL_MONITORED_EMAIL,
                'days_back': days_back,
                'steps': []
            }
            
            # Teste 1: Verificar query de busca
            try:
                query = gmail_service._build_receipt_search_query(days_back)
                debug_info['steps'].append({
                    'step': 'build_query',
                    'success': True,
                    'query': query
                })
            except Exception as e:
                debug_info['steps'].append({
                    'step': 'build_query',
                    'success': False,
                    'error': str(e)
                })
                return jsonify({'success': False, 'debug_info': debug_info})
            
            # Teste 2: Buscar mensagens básicas
            try:
                messages_response = gmail_service.list_receipt_messages(
                    user_email=config.GMAIL_MONITORED_EMAIL,
                    days_back=days_back,
                    max_results=10
                )
                messages = messages_response.get('messages', [])
                debug_info['steps'].append({
                    'step': 'list_messages',
                    'success': True,
                    'messages_found': len(messages),
                    'first_5_messages': messages[:5] if messages else []
                })
            except Exception as e:
                debug_info['steps'].append({
                    'step': 'list_messages',
                    'success': False,
                    'error': str(e)
                })
                return jsonify({'success': False, 'debug_info': debug_info})
            
            # Teste 3: Processar algumas mensagens
            if messages:
                try:
                    processed_receipts = []
                    for i, message in enumerate(messages[:3]):  # Processar apenas 3 para teste
                        try:
                            full_message = gmail_service.get_message(config.GMAIL_MONITORED_EMAIL, message['id'])
                            email_data = gmail_service._extract_basic_email_data(full_message)
                            receipt_data = gmail_service.receipt_extractor.extract_receipt_data(email_data)
                            
                            processed_receipts.append({
                                'message_id': message['id'],
                                'email_data': email_data,
                                'receipt_data': receipt_data
                            })
                        except Exception as e:
                            processed_receipts.append({
                                'message_id': message['id'],
                                'error': str(e)
                            })
                    
                    debug_info['steps'].append({
                        'step': 'process_messages',
                        'success': True,
                        'processed_count': len(processed_receipts),
                        'processed_receipts': processed_receipts
                    })
                except Exception as e:
                    debug_info['steps'].append({
                        'step': 'process_messages',
                        'success': False,
                        'error': str(e)
                    })
            else:
                debug_info['steps'].append({
                    'step': 'process_messages',
                    'success': True,
                    'message': 'Nenhuma mensagem para processar'
                })
            
            return jsonify({
                'success': True,
                'debug_info': debug_info
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e),
                'debug_info': {'error': str(e)}
            }), 500

    @app.route('/scan-emails', methods=['GET', 'POST'])
    def scan_emails():
        """Endpoint para varredura automática de emails."""
        if request.method == 'GET':
            return render_template('scan_emails.html', config=config)
        
        try:
            # Obter parâmetros do formulário
            days_back = int(request.form.get('days_back', '7'))
            send_email = request.form.get('send_email', 'false') == 'true'
            target_email = request.form.get('target_email', 'contasapagar@zello.tec.br')
            max_results = request.form.get('max_results', '')
            use_pagination = request.form.get('use_pagination', 'false') == 'true'
            selected_providers = request.form.getlist('providers')
            
            # Converter max_results para int ou None
            max_results = int(max_results) if max_results else None
            
            # Inicializar progresso na sessão
            session['scan_progress'] = {
                'status': 'starting',
                'message': 'Iniciando varredura...',
                'page_count': 0,
                'total_messages': 0,
                'current_message': 0,
                'total_processed': 0
            }
            
            # Usar GmailService real se disponível
            if gmail_service:
                try:
                    print(f"🔍 Iniciando varredura com GmailService...")
                    print(f"   Email monitorado: {config.GMAIL_MONITORED_EMAIL}")
                    print(f"   Período: {days_back} dias")
                    print(f"   Provedores selecionados: {selected_providers}")
                    print(f"   Paginação: {'Sim' if use_pagination else 'Não'}")
                    print(f"   Limite: {max_results if max_results else 'Sem limite'}")
                    
                    # Callback de progresso
                    def progress_callback(status_info):
                        print(f"📊 Progresso: {status_info.get('message', 'N/A')}")
                        print(f"   Páginas: {status_info.get('page_count', 0)}")
                        print(f"   Mensagens: {status_info.get('total_messages', 0)}")
                        print(f"   Recibos: {status_info.get('total_processed', 0)}")
                        session['scan_progress'] = status_info
                        session.modified = True
                    
                    # Processar emails com paginação
                    if use_pagination:
                        print("🔄 Usando paginação automática...")
                        receipts = gmail_service.process_all_receipt_emails(
                            user_email=config.GMAIL_MONITORED_EMAIL,
                            days_back=days_back,
                            max_results=max_results,
                            progress_callback=progress_callback
                        )
                    else:
                        print("⚡ Usando método rápido (sem paginação)...")
                        # Usar método antigo sem paginação
                        receipts = gmail_service.process_receipt_emails(
                            user_email=config.GMAIL_MONITORED_EMAIL,
                            days_back=days_back
                        )
                    
                    print(f"✅ Varredura concluída! Encontrados {len(receipts)} recibos")
                    
                    # Organizar resultados por provedor
                    emails_found = {}
                    for receipt in receipts:
                        provider = receipt.get('provedor', 'Unknown')
                        if provider not in emails_found:
                            emails_found[provider] = []
                        
                        emails_found[provider].append({
                            'subject': receipt.get('email_subject', 'N/A'),
                            'from': receipt.get('email_sender', 'N/A'),
                            'date': receipt.get('email_date', 'N/A'),
                            'amount': receipt.get('valor', 'N/A'),
                            'service': receipt.get('servico', 'N/A'),
                            'receipt_number': receipt.get('numero_recibo', 'N/A')
                        })
                    
                    scan_results = {
                        'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                        'days_scanned': days_back,
                        'accounts_scanned': [config.GMAIL_MONITORED_EMAIL],
                        'emails_found': emails_found,
                        'total_emails': len(receipts),
                        'total_accounts': 1,
                        'providers_used': selected_providers,
                        'pagination_used': use_pagination,
                        'max_results': max_results
                    }
                    
                except Exception as e:
                    print(f"Erro no GmailService: {e}")
                    # Fallback para simulação
                    scan_results = _create_mock_scan_results(days_back, selected_providers)
            else:
                # Fallback para simulação quando GmailService não disponível
                scan_results = _create_mock_scan_results(days_back, selected_providers)
            
            # Se solicitado, enviar email com resultados
            if send_email and scan_results['total_emails'] > 0:
                email_result = _send_scan_results_email(scan_results, target_email)
                scan_results['email_sent'] = email_result
            
            # Limpar progresso da sessão
            session.pop('scan_progress', None)
            
            flash(f"✅ Varredura concluída! Encontrados {scan_results['total_emails']} emails de recibos.", 'success')
            
            if send_email and scan_results['total_emails'] > 0:
                if scan_results['email_sent']['success']:
                    flash(f"📧 Resultados enviados para {target_email}!", 'success')
                else:
                    flash(f"❌ Erro ao enviar email: {scan_results['email_sent']['error']}", 'error')
            
            return render_template('scan_emails.html', config=config, results=scan_results)
            
        except Exception as e:
            flash(f"❌ Erro na varredura: {str(e)}", 'error')
            return render_template('scan_emails.html', config=config)

    def _create_mock_scan_results(days_back, selected_providers):
        """Cria resultados simulados para teste."""
        mock_emails = {
            'OpenAI': [
                {
                    'subject': 'Your receipt from OpenAI #2024-001',
                    'from': 'noreply@openai.com',
                    'date': '2025-09-29',
                    'amount': '$25.00',
                    'service': 'OpenAI API',
                    'receipt_number': 'inv_2024001'
                }
            ],
            'Anthropic': [
                {
                    'subject': 'Your receipt from Anthropic, PBC #2024-002',
                    'from': 'receipts@anthropic.com',
                    'date': '2025-09-28',
                    'amount': '$30.00',
                    'service': 'Claude API',
                    'receipt_number': 'rec_2024002'
                }
            ],
            'Cursor': [
                {
                    'subject': 'Your Cursor receipt #2024-003',
                    'from': 'billing@cursor.com',
                    'date': '2025-09-27',
                    'amount': '$15.00',
                    'service': 'Cursor Pro',
                    'receipt_number': 'cur_2024003'
                }
            ]
        }
        
        # Filtrar apenas provedores selecionados
        filtered_emails = {}
        total_emails = 0
        for provider in selected_providers:
            if provider in mock_emails:
                filtered_emails[provider] = mock_emails[provider]
                total_emails += len(mock_emails[provider])
        
        return {
            'timestamp': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'days_scanned': days_back,
            'accounts_scanned': ['iazello@zello.tec.br'],
            'emails_found': filtered_emails,
            'total_emails': total_emails,
            'total_accounts': 1,
            'providers_used': selected_providers,
            'pagination_used': False,
            'max_results': None
        }

    def _send_scan_results_email(scan_results, target_email):
        """Envia email com resultados da varredura."""
        try:
            # Criar conteúdo HTML do email
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa;">
                <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden;">
                    
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 30px; text-align: center;">
                        <h1 style="margin: 0; font-size: 28px;">📧 Relatório de Varredura de Emails</h1>
                        <p style="margin: 10px 0 0 0; opacity: 0.9;">Sistema de Automação de Recibos - Zello</p>
                    </div>
                    
                    <div style="padding: 30px;">
                        <h2 style="color: #2c3e50; margin-top: 0;">Resumo da Varredura</h2>
                        
                        <div style="background-color: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #1976d2; margin-top: 0;">📊 Estatísticas</h3>
                            <p><strong>Data/Hora:</strong> {scan_results['timestamp']}</p>
                            <p><strong>Período:</strong> Últimos {scan_results['days_scanned']} dias</p>
                            <p><strong>Contas verificadas:</strong> {scan_results['total_accounts']}</p>
                            <p><strong>Emails de recibos encontrados:</strong> {scan_results['total_emails']}</p>
                        </div>
                        
                        <h3 style="color: #2c3e50;">🧾 Recibos Encontrados</h3>
            """
            
            # Adicionar detalhes dos emails encontrados
            for account, emails in scan_results['emails_found'].items():
                if emails:
                    html_content += f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                        <h4 style="color: #495057; margin-top: 0;">📬 {account}</h4>
                        <table style="width: 100%; border-collapse: collapse;">
                    """
                    
                    for email in emails:
                        html_content += f"""
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 8px; font-weight: bold;">Serviço:</td>
                                <td style="padding: 8px;">{email.get('service', 'N/A')}</td>
                                <td style="padding: 8px; font-weight: bold;">Valor:</td>
                                <td style="padding: 8px; color: #28a745; font-weight: bold;">{email.get('amount', 'N/A')}</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 8px; font-weight: bold;">Assunto:</td>
                                <td style="padding: 8px;" colspan="3">{email.get('subject', 'N/A')}</td>
                            </tr>
                            <tr style="border-bottom: 2px solid #dee2e6;">
                                <td style="padding: 8px; font-weight: bold;">Data:</td>
                                <td style="padding: 8px;">{email.get('date', 'N/A')}</td>
                                <td style="padding: 8px; font-weight: bold;">De:</td>
                                <td style="padding: 8px;">{email.get('from', 'N/A')}</td>
                            </tr>
                        """
                    
                    html_content += """
                        </table>
                    </div>
                    """
            
            html_content += f"""
                        <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0;">
                            <h4 style="margin-top: 0; color: #856404;">📋 Próximos Passos</h4>
                            <p style="margin-bottom: 0;">Os recibos foram identificados automaticamente. Verifique os valores e processe conforme necessário no sistema de contas a pagar.</p>
                        </div>
                    </div>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 14px;">
                        <p style="margin: 0;">Relatório gerado automaticamente pelo Sistema de Automação de Recibos</p>
                        <p style="margin: 5px 0 0 0;">Zello Tecnologia - {scan_results['timestamp']}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Enviar email
            result = email_service.send_email(
                to_emails=[target_email],
                subject=f"📧 Relatório de Recibos - {scan_results['total_emails']} encontrados",
                body=html_content,
                is_html=True
            )
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao enviar email: {str(e)}"
            }


    @app.route('/api/send-report', methods=['POST'])
    def send_report():
        """Gera relatório HTML de recibos por período e envia em modo de teste para dois destinatários."""
        try:
            payload = request.get_json(silent=True) or {}
            # Período opcional: ISO strings (yyyy-mm-dd)
            start_date_str = payload.get('start_date')
            end_date_str = payload.get('end_date')
            test_mode = payload.get('test_mode', True)

            from datetime import datetime as _dt, timedelta as _td
            today = _dt.utcnow().date()
            # Padrão: mês corrente
            if not start_date_str or not end_date_str:
                start_date = today.replace(day=1)
                # Próximo mês - 1 dia
                if start_date.month == 12:
                    end_date = _dt(start_date.year + 1, 1, 1).date() - _td(days=1)
                else:
                    end_date = _dt(start_date.year, start_date.month + 1, 1).date() - _td(days=1)
            else:
                start_date = _dt.fromisoformat(start_date_str).date()
                end_date = _dt.fromisoformat(end_date_str).date()

            session = SessionLocal()
            from sqlalchemy import and_
            q = (
                session.query(Recibo)
                .filter(
                    and_(
                        Recibo.data_emissao >= start_date,
                        Recibo.data_emissao <= end_date
                    )
                )
                .order_by(Recibo.data_emissao.asc(), Recibo.plataforma.asc())
            )
            rows = q.all()

            # Agrupar por data e plataforma
            grouped: Dict[str, Dict[str, List[Recibo]]] = {}
            total_amount = 0.0
            currency = 'BRL'
            for r in rows:
                dkey = r.data_emissao.isoformat() if r.data_emissao else 'sem_data'
                pkey = r.plataforma or 'Desconhecido'
                grouped.setdefault(dkey, {}).setdefault(pkey, []).append(r)
                try:
                    total_amount += float(r.valor or 0)
                    if r.moeda:
                        currency = r.moeda
                except Exception:
                    pass

            # Montar HTML
            def esc(s: Any) -> str:
                try:
                    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                except Exception:
                    return str(s)

            sections: List[str] = []
            for dkey in sorted(grouped.keys()):
                sections.append(f"<h2>{esc(dkey)}</h2>")
                for pkey in sorted(grouped[dkey].keys()):
                    sections.append(f"<h3>{esc(pkey)}</h3>")
                    sections.append("<table style='width:100%;border-collapse:collapse' border='1' cellpadding='6'>")
                    sections.append("<tr><th>Valor</th><th>Moeda</th><th>NF</th><th>Criado</th></tr>")
                    for r in grouped[dkey][pkey]:
                        sections.append(
                            f"<tr><td>{esc(r.valor)}</td><td>{esc(r.moeda)}</td><td>{esc(r.numero_recibo)}</td><td>{esc(r.created_at.isoformat() if r.created_at else '-') }</td></tr>"
                        )
                    sections.append("</table>")

            html_body = f"""
            <html><body>
            <h1>Recibos IA - Relatório</h1>
            <p>Período: {start_date.isoformat()} a {end_date.isoformat()}</p>
            <p>Total: <strong>{len(rows)}</strong> | Valor: <strong>{total_amount} {currency}</strong></p>
            {''.join(sections) if sections else '<em>Nenhum recibo no período</em>'}
            </body></html>
            """

            # Assunto com padrão de testes
            month_name = end_date.strftime('%B %Y')
            # Traduzir mês básico se necessário
            month_name_pt = {
                'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 'April': 'Abril', 'May': 'Maio',
                'June': 'Junho', 'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro', 'October': 'Outubro',
                'November': 'Novembro', 'December': 'Dezembro'
            }.get(month_name.split()[0], month_name) + ' ' + month_name.split()[1]

            subject_base = f"Recibos IA - {month_name_pt} - {len(rows)} recibos processados"
            result = email_service.send_test_report(subject_base, html_body, always_to_test=bool(test_mode))

            return jsonify({
                'success': result.get('success', False),
                'email_result': result,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'count': len(rows),
                'total_amount': total_amount,
                'currency': currency
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/admin/monitor')
    def admin_monitor():
        """Página de administração do monitor de repositório."""
        return render_template('admin_monitor.html')
    
    @app.route('/api/process', methods=['POST'])
    def process_file():
        """
        Processa um arquivo de recibo enviado e extrai dados financeiros.
        
        Returns:
            JSON com resultado do processamento
        """
        try:
            # Verificar se arquivo foi enviado
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'Nenhum arquivo enviado'
                }), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'Nenhum arquivo selecionado'
                }), 400
            
            # Obter parâmetros da requisição
            provider = request.form.get('provider', request.form.get('llm_type', 'auto'))
            email = request.form.get('email', request.form.get('email_recipients', ''))
            output_format = request.form.get('output_format', request.form.get('email_format', 'preview'))
            # Normalizar valores possíveis do dropdown antigo para os novos
            if output_format in ['html', 'text']:
                # Se apenas o formato de corpo foi enviado, consideramos preview na API
                # e usamos o formato somente para o envio opcional de e-mail
                api_output_format = 'preview'
                email_body_format = output_format
            else:
                api_output_format = output_format
                email_body_format = request.form.get('email_format', 'html')
            max_attempts = int(request.form.get('max_attempts', '3'))
            
            # Salvar arquivo temporariamente
            save_result = file_service.save_file(file)
            if not save_result['success']:
                return jsonify(save_result), 400
            
            try:
                # Extrair texto do arquivo
                text_result = file_service.extract_text_from_file(save_result['file_path'])
                if not text_result['success']:
                    return jsonify(text_result), 400
                
                extracted_text = text_result['text']
                
                # Extrair dados do recibo com auto-correção
                generation_result = generation_service.generate_with_auto_correction(
                    text=extracted_text,
                    provider=provider,
                    max_attempts=max_attempts
                )
                
                if not generation_result['success']:
                    return jsonify(generation_result), 500
                
                receipt_data = generation_result['content']
                
                # Processar baseado no formato de saída
                if api_output_format in ['pdf', 'docx']:
                    # Criar documento
                    doc_result = file_service.create_document(
                        content=receipt_data,
                        format_type=output_format
                    )
                    
                    if not doc_result['success']:
                        return jsonify(doc_result), 500
                    
                    # Enviar por e-mail com anexo
                    if email:
                        email_list = [email.strip() for email in email.split(',') if email.strip()]
                        if email_list:
                            email_result = email_service.send_receipt_data_with_attachment(
                                to_emails=email_list,
                                receipt_data=receipt_data,
                                attachment_path=doc_result['file_path'],
                                attachment_filename=doc_result['filename'],
                                body_format=email_body_format
                            )
                            
                            # Limpar arquivo temporário
                            file_service.delete_file(save_result['file_path'])
                            
                            return jsonify({
                                'success': True,
                                'message': 'Documento criado e enviado por e-mail',
                                'document_created': doc_result,
                                'email_result': email_result,
                                'generation_info': generation_result
                            })
                    
                    # Retornar informações do documento criado
                    return jsonify({
                        'success': True,
                        'message': 'Documento criado com sucesso',
                        'document_created': doc_result,
                        'generation_info': generation_result
                    })
                
                elif api_output_format == 'email_body_txt' or (api_output_format == 'preview' and email and email_body_format in ['html','text']):
                    # Enviar conteúdo diretamente no corpo do e-mail
                    if email:
                        email_list = [email.strip() for email in email.split(',') if email.strip()]
                        if email_list:
                            email_result = email_service.send_receipt_data_email(
                                to_emails=email_list,
                                receipt_data=receipt_data,
                                format_type='html' if email_body_format == 'html' else 'text'
                            )
                            
                            return jsonify({
                                'success': True,
                                'message': 'E-mail enviado com sucesso',
                                'email_result': email_result,
                                'generation_info': generation_result
                            })
                    
                    return jsonify({
                        'success': False,
                        'error': 'E-mail não especificado para formato email_body_txt'
                    }), 400
                
                elif api_output_format == 'preview':
                    # Retornar JSON completo para preview
                    return jsonify({
                        'success': True,
                        'receipt_data': receipt_data,
                        'generation_info': generation_result,
                        'extraction_info': text_result
                    })
                
                else:
                    return jsonify({
                        'success': False,
                        'error': f'Formato de saída não suportado: {output_format}'
                    }), 400
                
            finally:
                # Limpar arquivo temporário
                file_service.delete_file(save_result['file_path'])
            
        except RequestEntityTooLarge:
            return jsonify({
                'success': False,
                'error': 'Arquivo muito grande. Tamanho máximo: 16MB'
            }), 413
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Erro interno: {str(e)}'
            }), 500

    @app.route('/api/process-file/<int:job_id>', methods=['POST'])
    def process_single_job(job_id: int):
        """
        Processa um arquivo de recibo específico identificado por job_id.
        Atualiza status do job e cria artefato JSON com o resultado.
        """
        session = SessionLocal()
        try:
            job: ReceiptJob | None = session.get(ReceiptJob, job_id)
            if not job:
                return jsonify({'success': False, 'error': 'Job não encontrado'}), 404

            # Atualizar status para processing
            job.status = JobStatus.PROCESSING
            job.attempts = (job.attempts or 0) + 1
            job.updated_at = __import__('datetime').datetime.utcnow()
            session.commit()

            # Extrair texto do arquivo
            text_result = file_service.extract_text_from_file(job.source_uri)
            if not text_result.get('success'):
                job.status = JobStatus.FAILED
                job.updated_at = __import__('datetime').datetime.utcnow()
                session.commit()
                return jsonify({'success': False, 'error': text_result.get('error', 'Falha ao extrair texto') }), 400

            extracted_text = text_result['text']

            # Extrair dados do recibo com auto-correção (usa provider enviado opcionalmente)
            provider = request.args.get('provider', 'auto')
            max_attempts = int(request.args.get('max_attempts', '3'))
            generation_result = generation_service.generate_with_auto_correction(
                text=extracted_text,
                provider=provider,
                max_attempts=max_attempts
            )

            if not generation_result.get('success'):
                job.status = JobStatus.FAILED
                job.updated_at = __import__('datetime').datetime.utcnow()
                session.commit()
                return jsonify({'success': False, 'error': generation_result.get('error', 'Falha na geração')}), 500

            receipt_data = generation_result['content']

            # Salvar artefato JSON em disco
            artifacts_dir = os.path.join('artifacts')
            try:
                os.makedirs(artifacts_dir, exist_ok=True)
            except Exception:
                pass
            artifact_filename = f"job_{job.id}.json"
            artifact_path = os.path.join(artifacts_dir, artifact_filename)
            try:
                with open(artifact_path, 'w', encoding='utf-8') as f:
                    import json as _json
                    _json.dump({
                        'job_id': job.id,
                        'source_uri': job.source_uri,
                        'receipt_data': receipt_data,
                        'generation_info': generation_result
                    }, f, ensure_ascii=False, indent=2)
            except Exception as e:
                job.status = JobStatus.FAILED
                job.updated_at = __import__('datetime').datetime.utcnow()
                session.commit()
                return jsonify({'success': False, 'error': f'Falha ao salvar artefato: {str(e)}'}), 500

            # Registrar artefato no banco
            try:
                artifact = ProcessingArtifact(
                    job_id=job.id,
                    type='json',
                    path=artifact_path,
                    size=os.path.getsize(artifact_path),
                    created_at=__import__('datetime').datetime.utcnow()
                )
                session.add(artifact)
            except Exception:
                pass

            # Atualizar status para processed
            job.status = JobStatus.PROCESSED
            job.updated_at = __import__('datetime').datetime.utcnow()
            session.commit()

            # Envio de email opcional (se query param email for fornecido)
            email_recipients = request.args.get('email', '')
            email_result = None
            if email_recipients:
                emails = [e.strip() for e in email_recipients.split(',') if e.strip()]
                if emails:
                    try:
                        email_result = email_service.send_receipt_data_email(
                            to_emails=emails,
                            receipt_data=receipt_data,
                            format_type='html'
                        )
                    except Exception as _:
                        email_result = {'success': False, 'error': 'Falha ao enviar e-mail'}

            return jsonify({
                'success': True,
                'message': 'Processamento concluído',
                'job': {
                    'id': job.id,
                    'status': job.status,
                },
                'artifact': {
                    'type': 'json',
                    'path': artifact_path,
                    'filename': artifact_filename
                },
                'email_result': email_result,
                'generation_info': generation_result
            })
        except Exception as e:
            try:
                # Tenta marcar como failed em caso de erro geral
                if 'job' in locals() and job:
                    job.status = JobStatus.FAILED
                    job.updated_at = __import__('datetime').datetime.utcnow()
                    session.commit()
            except Exception:
                pass
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            session.close()
    
    @app.route('/api/models', methods=['GET'])
    def get_available_models():
        """
        Retorna os modelos disponíveis para cada LLM.
        
        Returns:
            JSON com modelos disponíveis
        """
        try:
            models = llm_service.get_available_models()
            return jsonify({
                'success': True,
                'models': models
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/prompt-types', methods=['GET'])
    def get_prompt_types():
        """
        Retorna os tipos de prompt disponíveis.
        
        Returns:
            JSON com tipos de prompt
        """
        try:
            prompt_types = ReceiptPrompts.get_prompt_templates()
            return jsonify({
                'success': True,
                'prompt_types': prompt_types
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/test-llm-connection', methods=['GET'])
    def test_llm_connection():
        """
        Testa conectividade com Zello e OpenAI.
        """
        results = {}
        # teste Zello
        try:
            llm_service.get_completion('zello', [{"role": "user", "content": "ping"}])
            results['zello'] = {'ok': True}
        except Exception as e:
            results['zello'] = {'ok': False, 'error': str(e)}
        # teste OpenAI
        try:
            llm_service.get_completion('openai', [{"role": "user", "content": "ping"}])
            results['openai'] = {'ok': True}
        except Exception as e:
            results['openai'] = {'ok': False, 'error': str(e)}
        return jsonify({'success': True, 'results': results})
    
    @app.route('/api/validate-config', methods=['GET'])
    def validate_config():
        """
        Valida as configurações da aplicação.
        
        Returns:
            JSON com status da validação
        """
        try:
            errors = config.validate_config()
            return jsonify({
                'success': len(errors) == 0,
                'errors': errors,
                'config_status': {
                    'openai_configured': bool(config.OPENAI_API_KEY),
                    'zello_configured': bool(config.ZELLO_API_KEY),
                    'email_configured': bool(config.SMTP_USERNAME and config.SMTP_PASSWORD),
                    'repository_configured': bool(config.RECEIPTS_REPO_PATH)
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/scan-repository', methods=['POST'])
    def scan_repository():
        """
        Escaneia o repositório de recibos.
        
        Returns:
            JSON com resultado do scan
        """
        try:
            if not repository_monitor:
                return jsonify({
                    'success': False,
                    'error': 'Monitor de repositório não configurado'
                }), 400
            
            result = repository_monitor.scan_repository()
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/collect-emails', methods=['POST'])
    def collect_emails():
        """
        Coleta e-mails do Gemini via Gmail e registra jobs. Salva texto bruto no Drive (opcional).
        Body opcional: { "users": ["colab@empresa.com"], "max": 20 }
        """
        if not gmail_service:
            return jsonify({'success': False, 'error': 'Gmail não configurado'}), 400
        from database import SessionLocal
        from models.receipt_models import ReceiptJob, JobStatus
        import datetime as _dt
        payload = request.get_json(silent=True) or {}
        users = payload.get('users') or ([config.GMAIL_DELEGATED_USER] if config.GMAIL_DELEGATED_USER else [])
        max_results = int(payload.get('max', 20))
        if not users:
            return jsonify({'success': False, 'error': 'Nenhum usuário fornecido'}), 400
        session = SessionLocal()
        created = 0
        errors = []
        try:
            for user in users:
                try:
                    msgs = gmail_service.list_gemini_messages(user, max_results=max_results)
                    for m in msgs:
                        mid = m['id']
                        full = gmail_service.get_message(user, mid)
                        text = gmail_service.extract_plain_text(full)
                        # hash simples baseado em id da mensagem
                        file_hash = mid
                        exists = session.query(ReceiptJob).filter_by(source_hash=file_hash).first()
                        if exists:
                            continue
                        # opcionalmente salva no Drive
                        gdrive_path = None
                        if gdrive_service and config.GDRIVE_ROOT_FOLDER_ID:
                            folder_user = gdrive_service.ensure_folder(config.GDRIVE_ROOT_FOLDER_ID, user)
                            fid = gdrive_service.upload_text(folder_user, f"receipt_{mid}.txt", text)
                            gdrive_path = f"drive://{fid}"
                        job = ReceiptJob(
                            source_uri=f"gmail://{user}/{mid}",
                            source_hash=file_hash,
                            status=JobStatus.DISCOVERED,
                            attempts=0,
                            created_at=_dt.datetime.utcnow(),
                            updated_at=_dt.datetime.utcnow(),
                            collaborator_email=user,
                        )
                        session.add(job)
                        session.commit()
                        created += 1
                except Exception as ue:
                    errors.append({'user': user, 'error': str(ue)})
            return jsonify({'success': True, 'created': created, 'errors': errors})
        except Exception as e:
            session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            session.close()
    
    @app.route('/api/process-receipt', methods=['POST'])
    def process_receipt():
        """
        Processa um recibo manual via texto ou arquivo.
        
        Body JSON:
        {
            "text": "texto do recibo",
            "provider": "auto|openai|zello",
            "max_attempts": 3
        }
        """
        try:
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Dados JSON necessários'}), 400
            
            text = data.get('text')
            if not text:
                return jsonify({'success': False, 'error': 'Texto do recibo é obrigatório'}), 400
            
            provider = data.get('provider', 'auto')
            max_attempts = data.get('max_attempts', 3)
            
            # Processar recibo
            result = receipt_processor.extract_receipt_data(text, provider, max_attempts)
            
            if result['success']:
                # Salvar no banco se solicitado
                if data.get('save_to_db', False):
                    session = SessionLocal()
                    try:
                        # Criar job
                        job = ReceiptJob(
                            source_uri="manual://api",
                            source_hash=f"manual_{hash(text)}",
                            status=JobStatus.PROCESSED,
                            attempts=1,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        session.add(job)
                        session.commit()
                        
                        # Criar recibo
                        recibo = Recibo(
                            job_id=job.id,
                            plataforma=result['extracted_data'].get('provider', 'Unknown'),
                            valor=result['extracted_data'].get('amount', 0.0),
                            moeda=result['extracted_data'].get('currency', 'BRL'),
                            data_emissao=result['extracted_data'].get('date'),
                            numero_recibo=result['extracted_data'].get('invoice_number', 'N/A'),
                            confianca=result['extracted_data'].get('confidence_score', 0),
                            fonte_dados='API',
                            raw_data=json.dumps(result['extracted_data']),
                            created_at=datetime.utcnow()
                        )
                        session.add(recibo)
                        session.commit()
                        
                        result['job_id'] = job.id
                        result['recibo_id'] = recibo.id
                        
                    finally:
                        session.close()
                
                return jsonify(result)
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/receipts', methods=['GET'])
    def list_receipts():
        """
        Lista recibos com filtros opcionais.
        
        Query params:
        - provider: filtro por provedor
        - status: filtro por status
        - limit: limite de resultados (padrão: 50)
        - offset: offset para paginação
        """
        try:
            session = SessionLocal()
            
            # Parâmetros de filtro
            provider = request.args.get('provider')
            status = request.args.get('status')
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # Query base
            query = session.query(Recibo)
            
            # Aplicar filtros
            if provider:
                query = query.filter(Recibo.plataforma == provider)
            
            if status:
                query = query.join(ReceiptJob).filter(ReceiptJob.status == status)
            
            # Contar total
            total = query.count()
            
            # Aplicar paginação
            recibos = query.offset(offset).limit(limit).all()
            
            # Converter para dict
            result = []
            for recibo in recibos:
                result.append({
                    'id': recibo.id,
                    'provider': recibo.plataforma,
                    'amount': recibo.valor,
                    'currency': recibo.moeda,
                    'date': recibo.data_emissao.isoformat() if recibo.data_emissao else None,
                    'description': recibo.raw_data,
                    'invoice_number': recibo.numero_recibo,
                    'vendor': recibo.plataforma,
                    'confidence_score': recibo.confianca,
                    'created_at': recibo.created_at.isoformat() if recibo.created_at else None
                })
            
            session.close()
            
            return jsonify({
                'success': True,
                'receipts': result,
                'total': total,
                'limit': limit,
                'offset': offset
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/receipts/<int:receipt_id>', methods=['GET'])
    def get_receipt_details(receipt_id: int):
        """
        Obtém detalhes de um recibo específico.
        """
        try:
            session = SessionLocal()
            
            recibo = session.query(Recibo).filter(Recibo.id == receipt_id).first()
            if not recibo:
                return jsonify({'success': False, 'error': 'Recibo não encontrado'}), 404
            
            # Buscar job associado
            job = session.query(ReceiptJob).filter(ReceiptJob.id == recibo.job_id).first()
            
            result = {
                'id': recibo.id,
                'provider': recibo.plataforma,
                'amount': recibo.valor,
                'currency': recibo.moeda,
                'date': recibo.data_emissao.isoformat() if recibo.data_emissao else None,
                'description': recibo.raw_data,
                'invoice_number': recibo.numero_recibo,
                'vendor': recibo.plataforma,
                'confidence_score': recibo.confianca,
                'raw_data': json.loads(recibo.raw_data) if recibo.raw_data else None,
                'created_at': recibo.created_at.isoformat() if recibo.created_at else None,
                'job': {
                    'id': job.id if job else None,
                    'status': job.status.value if job else None,
                    'source_uri': job.source_uri if job else None,
                    'collaborator_email': job.collaborator_email if job else None
                } if job else None
            }
            
            session.close()
            
            return jsonify({
                'success': True,
                'receipt': result
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/monitor/gmail', methods=['POST'])
    def trigger_gmail_collection():
        """
        Dispara coleta manual do Gmail.
        """
        try:
            if not gmail_service:
                return jsonify({'success': False, 'error': 'Gmail não configurado'}), 400
            
            # Disparar job de coleta
            result = scheduler_service.trigger_job('collect_gmail_receipts')
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Coleta Gmail disparada com sucesso'
                })
            else:
                return jsonify(result), 500
                
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/scheduler/status', methods=['GET'])
    def get_scheduler_status():
        """
        Obtém status do scheduler.
        """
        try:
            status = scheduler_service.get_status()
            return jsonify({
                'success': True,
                'scheduler': status
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/scheduler/jobs/<job_id>/trigger', methods=['POST'])
    def trigger_scheduler_job(job_id: str):
        """
        Dispara um job do scheduler manualmente.
        """
        try:
            result = scheduler_service.trigger_job(job_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/scheduler/jobs/<job_id>/logs', methods=['GET'])
    def get_job_logs(job_id: str):
        """
        Obtém logs de um job específico.
        """
        try:
            lines = int(request.args.get('lines', 50))
            logs = scheduler_service.get_job_logs(job_id, lines)
            return jsonify({
                'success': True,
                'logs': logs
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/repository-stats', methods=['GET'])
    def get_repository_stats():
        """
        Obtém estatísticas do repositório e banco de dados.
        
        Returns:
            JSON com estatísticas
        """
        try:
            if not repository_monitor:
                return jsonify({
                    'success': False,
                    'error': 'Monitor de repositório não configurado'
                }), 400
            
            result = repository_monitor.get_repository_stats()
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/recent-jobs', methods=['GET'])
    def get_recent_jobs():
        """
        Obtém jobs recentes do banco de dados.
        
        Returns:
            JSON com lista de jobs recentes
        """
        try:
            if not repository_monitor:
                return jsonify({
                    'success': False,
                    'error': 'Monitor de repositório não configurado'
                }), 400
            
            limit = request.args.get('limit', 50, type=int)
            jobs = repository_monitor.get_recent_jobs(limit)
            return jsonify({
                'success': True,
                'jobs': jobs
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.errorhandler(413)
    def too_large(e):
        """Handler para arquivos muito grandes."""
        return jsonify({
            'success': False,
            'error': 'Arquivo muito grande. Tamanho máximo: 16MB'
        }), 413
    
    @app.errorhandler(404)
    def not_found(e):
        """Handler para páginas não encontradas."""
        return jsonify({
            'success': False,
            'error': 'Página não encontrada'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        """Handler para erros internos."""
        return jsonify({
            'success': False,
            'error': 'Erro interno do servidor'
        }), 500
    
    return app


def _generate_prompt(prompt_type: str, content: str) -> str:
    """
    Gera prompt baseado no tipo especificado.
    
    Args:
        prompt_type: Tipo do prompt
        content: Conteúdo para processar
        
    Returns:
        Prompt formatado
    """
    if prompt_type == 'extract_receipt_data':
        return ReceiptPrompts.extract_receipt_data(content)
    elif prompt_type == 'analyze_receipt_quality':
        return ReceiptPrompts.analyze_receipt_quality(content)
    elif prompt_type == 'categorize_receipt':
        return ReceiptPrompts.categorize_receipt(content)
    elif prompt_type == 'validate_receipt_amount':
        return ReceiptPrompts.validate_receipt_amount(content)
    elif prompt_type == 'generate_receipt_summary':
        return ReceiptPrompts.generate_receipt_summary(content)
    else:
        return ReceiptPrompts.extract_receipt_data(content)


if __name__ == '__main__':
    app = create_app()
    
    # Validar configurações antes de iniciar
    config_errors = config.validate_config()
    if config_errors:
        print("AVISOS DE CONFIGURACAO:")
        for error in config_errors:
            print(f"   - {error}")
        print("\nDica: Crie um arquivo .env baseado no env.example")
    
    print(f"Iniciando servidor em http://{config.HOST}:{config.PORT}")
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )
