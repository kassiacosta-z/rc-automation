#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automação Simples de Encaminhamento de Emails de Recibos de IA.

Funcionalidade:
1. Monitora iazello@zello.tec.br para emails de recibos
2. Filtra emails das plataformas de IA (OpenAI, Anthropic, Cursor, Manus, n8n)
3. Encaminha automaticamente para contasapagar@zello.tec.br
4. Marca como processado

Uso:
    python email_forwarder_final.py
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any

# Adicionar o diretório atual ao path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import config
from services.gmail_service import GmailService
from services.email_service import EmailService
from services.receipt_parser import parse_receipt_basic

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_forwarder.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Provedores de IA para filtrar
IA_PROVIDERS = [
    'openai.com',
    'anthropic.com', 
    'cursor.com',
    'manus.ai',
    'n8n.io',
    'gemini-noreply@google.com',  # Google AI
    'noreply@openai.com',
    'noreply@anthropic.com',
    'billing@openai.com',
    'billing@anthropic.com',
    'support@cursor.com',
    'billing@manus.ai',
    'noreply@n8n.io'
]

# Palavras-chave para identificar recibos
RECEIPT_KEYWORDS = [
    'invoice', 'recibo', 'fatura', 'bill', 'receipt',
    'billing', 'payment', 'pagamento', 'cobranca',
    'subscription', 'assinatura', 'usage', 'uso'
]


class EmailForwarder:
    """Encaminhador automático de emails de recibos de IA."""
    
    def __init__(self):
        """Inicializa o encaminhador."""
        self.gmail_service = None
        self.email_service = EmailService()
        self.processed_count = 0
        self.error_count = 0
        self._registry_path = os.path.join(os.path.dirname(__file__), 'processed_registry.json')
        self._registry = self._load_registry()
        
        # Inicializar Gmail Service
        if config.GOOGLE_CREDENTIALS_JSON and os.path.exists(config.GOOGLE_CREDENTIALS_JSON):
            try:
                # Tenta OAuth2 primeiro, depois Service Account
                use_oauth2 = os.path.exists("oauth2_credentials.json")
                if use_oauth2:
                    self.gmail_service = GmailService("oauth2_credentials.json", use_oauth2=True)
                    logger.info("Gmail Service inicializado com OAuth2")
                else:
                    self.gmail_service = GmailService(
                        config.GOOGLE_CREDENTIALS_JSON, 
                        delegated_user=config.GMAIL_DELEGATED_USER
                    )
                    logger.info("Gmail Service inicializado com Service Account")
            except Exception as e:
                logger.error(f"Erro ao inicializar Gmail Service: {e}")
                sys.exit(1)
        else:
            logger.error("GOOGLE_CREDENTIALS_JSON nao configurado ou arquivo nao encontrado")
            sys.exit(1)

    # -----------------------------
    # Registro de duplicatas (arquivo JSON simples)
    # -----------------------------
    def _load_registry(self) -> Dict[str, Any]:
        try:
            import json
            if os.path.exists(self._registry_path):
                with open(self._registry_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data.setdefault('by_invoice', {})
                    data.setdefault('by_triplet', {})
                    return data
        except Exception as e:
            logger.warning(f"Falha ao carregar registry: {e}")
        return {'by_invoice': {}, 'by_triplet': {}}

    def _save_registry(self) -> None:
        try:
            import json
            with open(self._registry_path, 'w', encoding='utf-8') as f:
                json.dump(self._registry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Falha ao salvar registry: {e}")

    def _make_triplet_key(self, provider: str | None, date_iso: str | None, amount: float | None) -> str:
        return f"{(provider or '').lower()}|{date_iso or ''}|{str(amount or '')}"

    def is_duplicate(self, receipt_email: Dict[str, Any]) -> bool:
        """Detecta duplicatas por número de recibo; fallback em (provider, date, amount)."""
        parsed = receipt_email.get('parsed') or {}
        invoice = (parsed.get('invoice_number') or '').strip()
        provider = (parsed.get('provider') or receipt_email.get('sender') or '').strip()
        # Extrair data ISO do texto já parseado se existir
        date_iso = None
        # Tentar achar data no body em ISO como fallback
        try:
            import re
            m = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", receipt_email.get('body') or '')
            if m:
                date_iso = m.group(0)
        except Exception:
            pass
        amount = parsed.get('amount')

        if invoice:
            if invoice in self._registry['by_invoice']:
                return True
        triplet = self._make_triplet_key(provider, date_iso, amount)
        if triplet in self._registry['by_triplet']:
            return True
        return False

    def register_processed(self, receipt_email: Dict[str, Any]) -> None:
        parsed = receipt_email.get('parsed') or {}
        invoice = (parsed.get('invoice_number') or '').strip()
        provider = (parsed.get('provider') or receipt_email.get('sender') or '').strip()
        # Data ISO fallback
        date_iso = None
        try:
            import re
            m = re.search(r"\b(20\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])\b", receipt_email.get('body') or '')
            if m:
                date_iso = m.group(0)
        except Exception:
            pass
        amount = parsed.get('amount')
        if invoice:
            self._registry['by_invoice'][invoice] = {
                'provider': provider,
                'date': date_iso,
                'amount': amount,
                'message_id': receipt_email.get('id')
            }
        triplet = self._make_triplet_key(provider, date_iso, amount)
        self._registry['by_triplet'][triplet] = {
            'invoice_number': invoice,
            'message_id': receipt_email.get('id')
        }
        self._save_registry()
    
    def is_ia_provider_email(self, sender: str) -> bool:
        """
        Verifica se o email é de um provedor de IA.
        
        Args:
            sender: Email do remetente
            
        Returns:
            True se for de provedor de IA
        """
        sender_lower = sender.lower()
        return any(provider in sender_lower for provider in IA_PROVIDERS)
    
    def is_receipt_email(self, subject: str, body: str) -> bool:
        """
        Verifica se o email é um recibo/fatura.
        
        Args:
            subject: Assunto do email
            body: Corpo do email
            
        Returns:
            True se for um recibo
        """
        text = f"{subject} {body}".lower()
        return any(keyword in text for keyword in RECEIPT_KEYWORDS)
    
    def get_receipt_emails(self, user_email: str, max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Busca emails de recibos de IA não processados, paginando até atingir o limite.
        
        Args:
            user_email: Email para monitorar
            max_results: Máximo de emails para buscar (paginado)
            
        Returns:
            Lista de emails de recibos
        """
        try:
            # Paginar usando a query abrangente do GmailService
            receipt_emails: List[Dict[str, Any]] = []
            fetched = 0
            page_token = None
            page_size = 100  # máximo permitido pela API para cada página
            
            while fetched < max_results:
                resp = self.gmail_service.list_receipt_messages(
                    user_email=user_email,
                    page_token=page_token,
                    max_results=min(page_size, max_results - fetched)
                )
                messages = resp.get('messages', [])
                page_token = resp.get('nextPageToken')
                
                if not messages:
                    break
            
                for msg_summary in messages:
                try:
                    # Obter detalhes completos do email
                    message = self.gmail_service.get_message(user_email, msg_summary['id'])
                    
                    # Extrair informações do email
                    headers = message.get('payload', {}).get('headers', [])
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                    
                    # Extrair corpo do email
                    body = self.gmail_service.extract_plain_text(message)
                    
                    # Verificar se é de provedor de IA e se é recibo
                    if (self.is_ia_provider_email(sender) and 
                        self.is_receipt_email(subject, body)):
                        
                        parsed = parse_receipt_basic(subject, body)
                        receipt_emails.append({
                            'id': msg_summary['id'],
                            'sender': sender,
                            'subject': subject,
                            'body': body,
                            'message': message,
                            'parsed': parsed
                        })
                        
                        logger.info(f"Recibo encontrado: {subject} de {sender}")
                        fetched += 1
                        if fetched >= max_results:
                            break
                
                except Exception as e:
                    logger.warning(f"Erro ao processar email {msg_summary['id']}: {e}")
                    continue
                
                if fetched >= max_results:
                    break
                
                if not page_token:
                    break
            
            return receipt_emails
            
        except Exception as e:
            logger.error(f"Erro ao buscar emails: {e}")
            return []
    
    def forward_email(self, receipt_email: Dict[str, Any], target_email: str) -> bool:
        """
        Encaminha um email de recibo para o email de destino.
        
        Args:
            receipt_email: Dados do email de recibo
            target_email: Email de destino
            
        Returns:
            True se encaminhado com sucesso
        """
        try:
            sender = receipt_email['sender']
            subject = receipt_email['subject']
            body = receipt_email['body']
            
            # Criar assunto para o encaminhamento
            # Se houver dados extraídos, enriquecer o assunto
            parsed = receipt_email.get('parsed') or {}
            prefix = ''
            if parsed.get('currency') and parsed.get('amount') is not None:
                prefix = f"[{parsed['currency']} {parsed['amount']}] "
            if parsed.get('invoice_number'):
                prefix += f"[NF {parsed['invoice_number']}] "
            forward_subject = f"[ENCAMINHADO] {prefix}{subject}"
            
            # Criar corpo do email encaminhado
            details_block = ""
            if parsed:
                details_block = (
                    "\n--- DADOS EXTRAIDOS ---\n"
                    f"Idioma: {parsed.get('language')}\n"
                    f"Valor: {parsed.get('amount')} {parsed.get('currency')} (match: {parsed.get('amount_match')})\n"
                    f"Numero Recibo: {parsed.get('invoice_number')}\n"
                )

            forward_body = f"""
Email original encaminhado automaticamente pelo sistema de automacao de recibos.

--- DADOS DO EMAIL ORIGINAL ---
De: {sender}
Assunto: {subject}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

{details_block}
--- CONTEUDO ORIGINAL ---
{body}

---
Este email foi processado automaticamente pelo sistema de automacao de recibos de IA.
            """.strip()
            
            # Enviar email
            success = self.email_service.send_email(
                to=[target_email],
                subject=forward_subject,
                body=forward_body
            )
            
            if success:
                logger.info(f"Email encaminhado: {subject} -> {target_email}")
                return True
            else:
                logger.error(f"Falha ao encaminhar: {subject}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao encaminhar email: {e}")
            return False
    
    def mark_as_processed(self, user_email: str, message_id: str) -> bool:
        """
        Marca um email como processado (adiciona label).
        
        Args:
            user_email: Email do usuário
            message_id: ID da mensagem
            
        Returns:
            True se marcado com sucesso
        """
        try:
            # Por simplicidade, vamos apenas logar que foi processado
            # Em uma implementação real, você adicionaria uma label específica
            logger.info(f"Email {message_id} marcado como processado")
            return True
        except Exception as e:
            logger.error(f"Erro ao marcar email como processado: {e}")
            return False
    
    def run_forwarding(self, source_email: str, target_email: str) -> Dict[str, Any]:
        """
        Executa o processo completo de encaminhamento.
        
        Args:
            source_email: Email para monitorar
            target_email: Email de destino
            
        Returns:
            Relatório da execução
        """
        logger.info(f"Iniciando encaminhamento de {source_email} para {target_email}")
        
        start_time = datetime.now()
        
        try:
            # Buscar emails de recibos
            receipt_emails = self.get_receipt_emails(source_email)
            
            if not receipt_emails:
                logger.info("Nenhum recibo encontrado")
                return {
                    'success': True,
                    'processed': 0,
                    'errors': 0,
                    'message': 'Nenhum recibo encontrado'
                }
            
            logger.info(f"Encontrados {len(receipt_emails)} recibos para processar")
            
            # Processar cada email
            for receipt_email in receipt_emails:
                try:
                    # Evitar duplicatas
                    if self.is_duplicate(receipt_email):
                        logger.info(f"Ignorado duplicata: {receipt_email.get('subject')}")
                        continue
                    # Encaminhar email
                    if self.forward_email(receipt_email, target_email):
                        self.processed_count += 1
                        
                        # Marcar como processado
                        self.mark_as_processed(source_email, receipt_email['id'])
                        self.register_processed(receipt_email)
                    else:
                        self.error_count += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao processar email {receipt_email['id']}: {e}")
                    self.error_count += 1
            
            # Relatório final
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'processed': self.processed_count,
                'errors': self.error_count,
                'total_found': len(receipt_emails),
                'duration_seconds': duration,
                'message': f'Processados: {self.processed_count}, Erros: {self.error_count}'
            }
            
            logger.info(f"Processo concluido em {duration:.2f}s - {result['message']}")
            return result
            
        except Exception as e:
            logger.error(f"Erro geral no processo: {e}")
            return {
                'success': False,
                'processed': self.processed_count,
                'errors': self.error_count + 1,
                'message': f'Erro: {str(e)}'
            }


def main():
    """Função principal."""
    logger.info("=" * 60)
    logger.info("AUTOMACAO DE ENCAMINHAMENTO DE RECIBOS DE IA")
    logger.info("=" * 60)
    
    # Verificar configurações
    if not config.GMAIL_MONITORED_EMAIL:
        logger.error("GMAIL_MONITORED_EMAIL nao configurado")
        sys.exit(1)
    
    if not config.REPORTS_EMAIL:
        logger.error("REPORTS_EMAIL nao configurado")
        sys.exit(1)
    
    # Inicializar encaminhador
    forwarder = EmailForwarder()
    
    # Executar encaminhamento
    result = forwarder.run_forwarding(
        source_email=config.GMAIL_MONITORED_EMAIL,
        target_email=config.REPORTS_EMAIL
    )
    
    # Exibir resultado
    if result['success']:
        logger.info(f"SUCESSO: {result['message']}")
        sys.exit(0)
    else:
        logger.error(f"FALHA: {result['message']}")
        sys.exit(1)


if __name__ == '__main__':
    main()
