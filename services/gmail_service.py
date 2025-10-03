"""
Integração com Gmail API para coleta de e-mails de recibos de IA.
Suporta OAuth2 e Domain-Wide Delegation (DWD) via service account.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Callable
import base64
import re
import os
import json
import pickle
import time
from datetime import datetime, timedelta

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .receipt_extractor import ReceiptExtractor


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailService:
    def __init__(self, credentials_json_path: str, delegated_user: Optional[str] = None, use_oauth2: bool = False):
        self.credentials_json_path = credentials_json_path
        self.delegated_user = delegated_user
        self.use_oauth2 = use_oauth2
        self._service = None
        self._token_file = "token.pickle" if use_oauth2 else None
        
        # Inicializar ReceiptExtractor
        self.receipt_extractor = ReceiptExtractor()
        
        # Configurações de rate limiting
        self.rate_limit_delay = 0.1  # Delay entre requests (segundos)
        self.max_retries = 3  # Máximo de tentativas em caso de erro
        self.quota_exceeded_delay = 60  # Delay quando quota excedida (segundos)

    def _get_service(self):
        if self._service:
            return self._service
        
        if self.use_oauth2:
            creds = self._get_oauth2_credentials()
        else:
            creds = self._get_service_account_credentials()
        
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    def _get_service_account_credentials(self):
        """Obtém credenciais via Service Account (Domain-wide Delegation)."""
        creds = service_account.Credentials.from_service_account_file(
            self.credentials_json_path, scopes=GMAIL_SCOPES
        )
        if self.delegated_user:
            creds = creds.with_subject(self.delegated_user)
        return creds

    def _get_oauth2_credentials(self):
        """Obtém credenciais via OAuth2 (mais simples, não requer DWD)."""
        creds = None
        
        # Carrega token existente se disponível
        if os.path.exists(self._token_file):
            with open(self._token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Se não há credenciais válidas, faz o fluxo OAuth2
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_json_path, GMAIL_SCOPES
                )
                # Usar fluxo manual (mais compatível)
                # Direciona o login para a conta esperada (não é possível usar URL do Inbox aqui)
                # login_hint ajuda o Google a pré-selecionar a conta correta
                login_hint = self.delegated_user or os.getenv('GMAIL_MONITORED_EMAIL') or None
                if login_hint:
                    auth_url, _ = flow.authorization_url(
                        prompt='consent',
                        access_type='offline',
                        include_granted_scopes='true',
                        login_hint=login_hint,
                    )
                else:
                    auth_url, _ = flow.authorization_url(
                        prompt='consent',
                        access_type='offline',
                        include_granted_scopes='true',
                    )
                print("=" * 60)
                print("AUTORIZAÇÃO OAUTH2 NECESSÁRIA")
                print("=" * 60)
                print("1. Abra esta URL no navegador:")
                print(f"   {auth_url}")
                print("\n2. Faça login com: iazello@zello.tec.br")
                print("3. Autorize o acesso ao Gmail")
                print("4. Copie o código de autorização")
                print("=" * 60)
                
                code = input("Cole aqui o código de autorização: ").strip()
                if not code:
                    raise Exception("Código de autorização não fornecido")
                
                flow.fetch_token(code=code)
                creds = flow.credentials
            
            # Salva as credenciais para próxima execução
            with open(self._token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

    def list_gemini_messages(self, user_email: str, max_results: int = 50) -> List[Dict[str, Any]]:
        service = self._get_service()
        query = 'from:gemini-noreply@google.com'
        try:
            resp = service.users().messages().list(
                userId=user_email, q=query, maxResults=max_results
            ).execute()
            return resp.get("messages", [])
        except HttpError as e:
            raise Exception(f"Erro Gmail list: {e}")

    # ==========================
    # Filtros abrangentes para recibos de IA (multilíngue)
    # ==========================
    @staticmethod
    def get_receipt_search_query() -> str:
        return (
            "(from:invoice+statements@mail.anthropic.com OR "
            "from:invoice+statements+acct_1R15XBHkfKp4fCS9@stripe.com OR "
            "from:help@paddle.com OR "
            "from:billing@openai.com OR "
            "from:noreply@cursor.com OR "
            "from:noreply@manus.ai) "
            "AND "
            "(subject:receipt OR subject:recibo OR subject:invoice OR subject:fatura OR "
            "subject:billing OR subject:cobranca OR subject:transacao OR subject:transaction OR "
            "subject:\"Your receipt from\" OR subject:\"Seu recibo de\" OR subject:\"Transacao da subscricao\")"
        )

    def list_receipt_messages(self, user_email: str, page_token: Optional[str] = None, max_results: int = 100, days_back: int = 7) -> Dict[str, Any]:
        """Lista mensagens de recibos abrangendo histórico completo (paginável)."""
        service = self._get_service()
        query = self._build_receipt_search_query(days_back)
        try:
            req = service.users().messages().list(
                userId=user_email,
                q=query,
                includeSpamTrash=True,
                maxResults=max_results,
                pageToken=page_token
            )
            resp = req.execute()
            return {
                'messages': resp.get('messages', []),
                'nextPageToken': resp.get('nextPageToken')
            }
        except HttpError as e:
            raise Exception(f"Erro Gmail list (receipts): {e}")

    def list_by_query(self, user_email: str, query: str, page_token: Optional[str] = None, max_results: int = 100, include_spam_trash: bool = True) -> Dict[str, Any]:
        """Lista mensagens por query arbitrária, com paginação.

        Args:
            user_email: caixa alvo
            query: string de busca do Gmail
            page_token: token de próxima página
            max_results: até 100 por página
            include_spam_trash: inclui spam/lixeira
        """
        service = self._get_service()
        try:
            resp = service.users().messages().list(
                userId=user_email,
                q=query,
                includeSpamTrash=include_spam_trash,
                maxResults=max_results,
                pageToken=page_token
            ).execute()
            return {
                'messages': resp.get('messages', []),
                'nextPageToken': resp.get('nextPageToken')
            }
        except HttpError as e:
            raise Exception(f"Erro Gmail list (custom): {e}")

    def get_message(self, user_email: str, message_id: str) -> Dict[str, Any]:
        service = self._get_service()
        try:
            return service.users().messages().get(userId=user_email, id=message_id, format="full").execute()
        except HttpError as e:
            raise Exception(f"Erro Gmail get: {e}")

    def extract_plain_text(self, message: Dict[str, Any]) -> str:
        # Procura partes text/plain preferencialmente
        payload = message.get("payload", {})
        parts = payload.get("parts", [])
        if parts:
            for part in parts:
                if part.get("mimeType") == "text/plain" and "data" in part.get("body", {}):
                    data = part["body"]["data"]
                    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")
        # Fallback: corpo simples
        body = payload.get("body", {}).get("data")
        if body:
            return base64.urlsafe_b64decode(body.encode()).decode("utf-8", errors="replace")
        return ""

    def process_receipt_emails(self, user_email: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Processa emails de recibos usando ReceiptExtractor.
        
        Args:
            user_email: Email do usuário para buscar
            days_back: Número de dias para buscar no passado
            
        Returns:
            Lista estruturada de recibos processados
        """
        try:
            # Buscar emails dos provedores de IA
            query = self._build_receipt_search_query(days_back)
            messages_response = self.list_messages(user_email, query)
            
            processed_receipts = []
            
            for message in messages_response.get('messages', []):
                try:
                    # Obter dados completos do email
                    message_id = message['id']
                    full_message = self.get_message(user_email, message_id)
                    
                    # Extrair dados básicos do email
                    email_data = self._extract_basic_email_data(full_message)
                    
                    # Usar ReceiptExtractor para extrair dados estruturados
                    receipt_data = self.receipt_extractor.extract_receipt_data(email_data)
                    
                    if receipt_data.get('success', False):
                        # Adicionar metadados do email
                        receipt_data.update({
                            'message_id': message_id,
                            'email_date': email_data.get('date'),
                            'email_subject': email_data.get('subject'),
                            'email_sender': email_data.get('sender'),
                            'processed_at': datetime.now().isoformat()
                        })
                        
                        processed_receipts.append(receipt_data)
                    
                except Exception as e:
                    print(f"Erro ao processar email {message.get('id', 'unknown')}: {e}")
                    continue
            
            return processed_receipts
            
        except Exception as e:
            raise Exception(f"Erro ao processar emails de recibos: {e}")

    def get_enhanced_email_data(self, user_email: str, message_id: str) -> Dict[str, Any]:
        """
        Extrai dados completos de um email específico usando ReceiptExtractor.
        
        Args:
            user_email: Email do usuário
            message_id: ID da mensagem
            
        Returns:
            Dados estruturados do email e recibo
        """
        try:
            # Obter conteúdo completo do email
            full_message = self.get_message(user_email, message_id)
            
            # Extrair dados básicos do email
            email_data = self._extract_basic_email_data(full_message)
            
            # Usar ReceiptExtractor para extrair dados estruturados
            receipt_data = self.receipt_extractor.extract_receipt_data(email_data)
            
            # Combinar dados do email com dados extraídos
            enhanced_data = {
                'email_info': {
                    'message_id': message_id,
                    'sender': email_data.get('sender'),
                    'subject': email_data.get('subject'),
                    'date': email_data.get('date'),
                    'body': email_data.get('body'),
                    'headers': email_data.get('headers', {})
                },
                'receipt_data': receipt_data,
                'extraction_metadata': {
                    'extracted_at': datetime.now().isoformat(),
                    'provider_identified': receipt_data.get('provedor') != 'Desconhecido',
                    'data_completeness': self._calculate_data_completeness(receipt_data)
                }
            }
            
            return enhanced_data
            
        except Exception as e:
            raise Exception(f"Erro ao extrair dados do email {message_id}: {e}")

    def _build_receipt_search_query(self, days_back: int) -> str:
        """
        Constrói query de busca para emails de recibos de IA.
        
        Args:
            days_back: Número de dias para buscar no passado
            
        Returns:
            Query string para Gmail API
        """
        # Data de início da busca
        start_date = datetime.now() - timedelta(days=days_back)
        date_str = start_date.strftime('%Y/%m/%d')
        
        # Obter emails de todos os provedores suportados
        provider_emails = []
        for provider, emails in self.receipt_extractor.ia_providers.items():
            provider_emails.extend(emails)
        
        # Construir query com remetentes
        sender_query = ' OR '.join([f'from:{email}' for email in provider_emails])
        
        # Query completa
        query = f"({sender_query}) after:{date_str}"
        
        return query

    def _extract_basic_email_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extrai dados básicos de um email.
        
        Args:
            message: Dados completos da mensagem do Gmail
            
        Returns:
            Dicionário com dados básicos do email
        """
        try:
            # Extrair headers
            headers = message.get('payload', {}).get('headers', [])
            header_dict = {h['name'].lower(): h['value'] for h in headers}
            
            # Extrair dados básicos
            sender = header_dict.get('from', '')
            subject = header_dict.get('subject', '')
            date = header_dict.get('date', '')
            
            # Extrair corpo do email
            body = self.extract_plain_text(message)
            
            return {
                'sender': sender,
                'subject': subject,
                'date': date,
                'body': body,
                'headers': header_dict
            }
            
        except Exception as e:
            print(f"Erro ao extrair dados básicos do email: {e}")
            return {
                'sender': '',
                'subject': '',
                'date': '',
                'body': '',
                'headers': {}
            }

    def _calculate_data_completeness(self, receipt_data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Calcula a completude dos dados extraídos.
        
        Args:
            receipt_data: Dados extraídos do recibo
            
        Returns:
            Dicionário indicando quais campos foram extraídos com sucesso
        """
        return {
            'provider': bool(receipt_data.get('provedor') and receipt_data.get('provedor') != 'Desconhecido'),
            'value': bool(receipt_data.get('valor')),
            'date': bool(receipt_data.get('data')),
            'receipt_number': bool(receipt_data.get('numero_recibo')),
            'service': bool(receipt_data.get('servico'))
        }

    def get_receipt_providers_info(self) -> Dict[str, Any]:
        """
        Retorna informações sobre provedores de IA suportados.
        
        Returns:
            Dicionário com informações dos provedores
        """
        return {
            'supported_providers': self.receipt_extractor.get_supported_providers(),
            'provider_emails': {
                provider: self.receipt_extractor.get_provider_emails(provider)
                for provider in self.receipt_extractor.get_supported_providers()
            },
            'total_providers': len(self.receipt_extractor.get_supported_providers()),
            'total_emails': sum(len(emails) for emails in self.receipt_extractor.ia_providers.values())
        }

    def get_all_receipt_messages(self, user_email: str, query: str, 
                                max_results: Optional[int] = None,
                                progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        Coleta todas as mensagens de recibos com paginação automática.
        
        Args:
            user_email: Email do usuário para buscar
            query: Query de busca Gmail
            max_results: Limite máximo de resultados (None = sem limite)
            progress_callback: Função para reportar progresso
            
        Returns:
            Lista completa de mensagens encontradas
        """
        all_messages = []
        page_token = None
        page_count = 0
        total_found = 0
        
        try:
            while True:
                # Verificar limite de resultados
                if max_results and total_found >= max_results:
                    if progress_callback:
                        progress_callback({
                            'status': 'completed',
                            'message': f'Limite de {max_results} resultados atingido',
                            'page_count': page_count,
                            'total_messages': total_found
                        })
                    break
                
                # Buscar página atual
                page_messages, next_page_token = self._fetch_page_with_retry(
                    user_email, query, page_token, max_results, total_found
                )
                
                # Adicionar mensagens à lista total
                all_messages.extend(page_messages)
                total_found += len(page_messages)
                page_count += 1
                
                # Callback de progresso
                if progress_callback:
                    progress_callback({
                        'status': 'processing',
                        'message': f'Página {page_count} processada - {len(page_messages)} mensagens encontradas',
                        'page_count': page_count,
                        'total_messages': total_found,
                        'messages_in_page': len(page_messages)
                    })
                
                # Verificar se há próxima página
                if not next_page_token:
                    if progress_callback:
                        progress_callback({
                            'status': 'completed',
                            'message': 'Todas as páginas processadas',
                            'page_count': page_count,
                            'total_messages': total_found
                        })
                    break
                
                page_token = next_page_token
                
                # Rate limiting - delay entre requests
                time.sleep(self.rate_limit_delay)
            
            return all_messages
            
        except Exception as e:
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'message': f'Erro durante paginação: {str(e)}',
                    'page_count': page_count,
                    'total_messages': total_found
                })
            raise Exception(f"Erro na paginação de mensagens: {e}")

    def _fetch_page_with_retry(self, user_email: str, query: str, page_token: Optional[str], 
                              max_results: Optional[int], current_total: int) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Busca uma página de mensagens com retry automático.
        
        Args:
            user_email: Email do usuário
            query: Query de busca
            page_token: Token da página atual
            max_results: Limite máximo de resultados
            current_total: Total atual de mensagens encontradas
            
        Returns:
            Tupla com (mensagens_da_página, próximo_page_token)
        """
        for attempt in range(self.max_retries):
            try:
                # Calcular quantas mensagens buscar nesta página
                page_size = 100  # Tamanho padrão da página
                if max_results:
                    remaining = max_results - current_total
                    page_size = min(page_size, remaining)
                
                # Fazer request para a página
                service = self._get_service()
                request_params = {
                    'userId': user_email,
                    'q': query,
                    'maxResults': page_size,
                    'includeSpamTrash': True
                }
                
                if page_token:
                    request_params['pageToken'] = page_token
                
                response = service.users().messages().list(**request_params).execute()
                
                messages = response.get('messages', [])
                next_page_token = response.get('nextPageToken')
                
                return messages, next_page_token
                
            except HttpError as e:
                if e.resp.status == 429:  # Quota exceeded
                    if attempt < self.max_retries - 1:
                        print(f"Quota excedida. Aguardando {self.quota_exceeded_delay}s antes de tentar novamente...")
                        time.sleep(self.quota_exceeded_delay)
                        continue
                    else:
                        raise Exception(f"Quota excedida após {self.max_retries} tentativas")
                elif e.resp.status in [500, 502, 503, 504]:  # Server errors
                    if attempt < self.max_retries - 1:
                        delay = 2 ** attempt  # Exponential backoff
                        print(f"Erro do servidor. Aguardando {delay}s antes de tentar novamente...")
                        time.sleep(delay)
                        continue
                    else:
                        raise Exception(f"Erro do servidor após {self.max_retries} tentativas: {e}")
                else:
                    raise Exception(f"Erro Gmail API: {e}")
            
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = 1 * (attempt + 1)  # Linear backoff
                    print(f"Erro inesperado. Aguardando {delay}s antes de tentar novamente...")
                    time.sleep(delay)
                    continue
                else:
                    raise Exception(f"Erro após {self.max_retries} tentativas: {e}")
        
        return [], None

    def process_all_receipt_emails(self, user_email: str, days_back: int = 30, 
                                 max_results: Optional[int] = None,
                                 progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> List[Dict[str, Any]]:
        """
        Processa todos os emails de recibos com paginação automática.
        
        Args:
            user_email: Email do usuário para buscar
            days_back: Número de dias para buscar no passado
            max_results: Limite máximo de resultados (None = sem limite)
            progress_callback: Função para reportar progresso
            
        Returns:
            Lista estruturada de todos os recibos processados
        """
        try:
            # Construir query de busca
            query = self._build_receipt_search_query(days_back)
            
            # Buscar todas as mensagens com paginação
            all_messages = self.get_all_receipt_messages(
                user_email, query, max_results, progress_callback
            )
            
            # Processar cada mensagem
            processed_receipts = []
            total_messages = len(all_messages)
            
            for idx, message in enumerate(all_messages):
                try:
                    # Callback de progresso para processamento
                    if progress_callback:
                        progress_callback({
                            'status': 'processing_receipts',
                            'message': f'Processando recibo {idx + 1}/{total_messages}',
                            'current_message': idx + 1,
                            'total_messages': total_messages
                        })
                    
                    # Obter dados completos do email
                    message_id = message['id']
                    full_message = self.get_message(user_email, message_id)
                    
                    # Extrair dados básicos do email
                    email_data = self._extract_basic_email_data(full_message)
                    
                    # Usar ReceiptExtractor para extrair dados estruturados
                    receipt_data = self.receipt_extractor.extract_receipt_data(email_data)
                    
                    if receipt_data.get('success', False):
                        # Adicionar metadados do email
                        receipt_data.update({
                            'message_id': message_id,
                            'email_date': email_data.get('date'),
                            'email_subject': email_data.get('subject'),
                            'email_sender': email_data.get('sender'),
                            'processed_at': datetime.now().isoformat()
                        })
                        
                        processed_receipts.append(receipt_data)
                    
                    # Rate limiting entre processamentos
                    time.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    print(f"Erro ao processar email {message.get('id', 'unknown')}: {e}")
                    continue
            
            # Callback final
            if progress_callback:
                progress_callback({
                    'status': 'completed',
                    'message': f'Processamento concluído - {len(processed_receipts)} recibos extraídos',
                    'total_processed': len(processed_receipts),
                    'total_messages': total_messages
                })
            
            return processed_receipts
            
        except Exception as e:
            if progress_callback:
                progress_callback({
                    'status': 'error',
                    'message': f'Erro no processamento: {str(e)}',
                    'total_processed': len(processed_receipts) if 'processed_receipts' in locals() else 0
                })
            raise Exception(f"Erro ao processar todos os emails de recibos: {e}")

    def set_rate_limiting(self, delay: float = 0.1, max_retries: int = 3, 
                         quota_delay: int = 60) -> None:
        """
        Configura parâmetros de rate limiting.
        
        Args:
            delay: Delay entre requests (segundos)
            max_retries: Máximo de tentativas em caso de erro
            quota_delay: Delay quando quota excedida (segundos)
        """
        self.rate_limit_delay = delay
        self.max_retries = max_retries
        self.quota_exceeded_delay = quota_delay


