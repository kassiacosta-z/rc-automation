"""
Serviço para envio de e-mails.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from config import config


class EmailService:
    """Serviço para envio de e-mails."""
    
    def __init__(self):
        """Inicializa o serviço de e-mail."""
        self.smtp_server = config.SMTP_SERVER
        self.smtp_port = config.SMTP_PORT
        self.username = config.SMTP_USERNAME
        self.password = config.SMTP_PASSWORD
        self.from_email = config.EMAIL_FROM
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Envia um e-mail.
        
        Args:
            to_emails: Lista de e-mails destinatários
            subject: Assunto do e-mail
            body: Corpo do e-mail
            is_html: Se o corpo é HTML
            attachments: Lista de anexos (opcional)
            
        Returns:
            Dicionário com resultado do envio
            
        Raises:
            Exception: Se houver erro no envio
        """
        if not all([self.username, self.password, self.from_email]):
            return {
                "success": False,
                "error": "Configurações de e-mail não definidas"
            }
        
        try:
            # Criar mensagem
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Adicionar corpo
            if is_html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Adicionar anexos se houver
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Conectar e enviar
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return {
                "success": True,
                "message": f"E-mail enviado com sucesso para {len(to_emails)} destinatário(s)"
            }
            
        except smtplib.SMTPAuthenticationError as e:
            return {
                "success": False,
                "error": f"Erro de autenticação SMTP: {str(e)}"
            }
        except smtplib.SMTPException as e:
            return {
                "success": False,
                "error": f"Erro SMTP: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro inesperado: {str(e)}"
            }

    def send_test_report(
        self,
        base_subject: str,
        html_body: str,
        always_to_test: bool = True
    ) -> Dict[str, Any]:
        """
        Envia relatório em modo de teste para dois destinatários (teste + contas a pagar).
        
        Args:
            base_subject: Assunto base sem prefixo
            html_body: Corpo em HTML já formatado
            always_to_test: Se True, envia para ambos (teste + contas)
        
        Returns:
            Resultado do envio
        """
        to_emails: List[str] = []
        subject = base_subject
        if always_to_test:
            subject = f"[TESTE] {base_subject}"
            to_emails = [
                'kassia.mf.costa@gmail.com',
                'contasapagar@zello.tec.br'
            ]
        else:
            to_emails = ['contasapagar@zello.tec.br']

        return self.send_email(
            to_emails=to_emails,
            subject=subject,
            body=html_body,
            is_html=True
        )
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]) -> None:
        """
        Adiciona um anexo à mensagem.
        
        Args:
            msg: Mensagem MIME
            attachment: Dicionário com dados do anexo
        """
        filename = attachment.get('filename', 'attachment')
        content = attachment.get('content', b'')
        content_type = attachment.get('content_type', 'application/octet-stream')
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(content)
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename= {filename}'
        )
        msg.attach(part)
    
    def send_receipt_data_email(
        self,
        to_emails: List[str],
        receipt_data: str,
        format_type: str = "html"
    ) -> Dict[str, Any]:
        """
        Envia e-mail com dados de recibo formatados.
        
        Args:
            to_emails: Lista de e-mails destinatários
            receipt_data: Dados extraídos do recibo
            format_type: Tipo de formatação ("html" ou "text")
            
        Returns:
            Dicionário com resultado do envio
        """
        subject = "Dados de Recibo de IA - Processamento Automatizado"
        
        if format_type.lower() == "html":
            body = self._format_receipt_data_html(receipt_data)
            is_html = True
        else:
            body = self._format_receipt_data_text(receipt_data)
            is_html = False
        
        return self.send_email(to_emails, subject, body, is_html)
    
    def send_user_stories_email(
        self,
        to_emails: List[str],
        user_stories: str,
        format_type: str = "html"
    ) -> Dict[str, Any]:
        """
        Envia e-mail com Histórias de Usuário formatadas.
        
        Args:
            to_emails: Lista de e-mails destinatários
            user_stories: Texto das Histórias de Usuário
            format_type: Tipo de formatação ("html" ou "text")
            
        Returns:
            Dicionário com resultado do envio
        """
        subject = "Histórias de Usuário - Processamento Automatizado"
        
        if format_type.lower() == "html":
            body = self._format_user_stories_html(user_stories)
            is_html = True
        else:
            body = self._format_user_stories_text(user_stories)
            is_html = False
        
        return self.send_email(to_emails, subject, body, is_html)
    
    def _format_receipt_data_html(self, receipt_data: str) -> str:
        """
        Formata dados de recibo em HTML.
        
        Args:
            receipt_data: Dados extraídos do recibo
            
        Returns:
            HTML formatado
        """
        # Converter JSON para HTML se necessário
        try:
            import json
            data = json.loads(receipt_data)
            html_content = self._json_to_html_receipt(data)
        except:
            html_content = receipt_data
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Dados de Recibo de IA</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f8f9fa;
                    color: #333;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
                    color: white; 
                    padding: 30px; 
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                    font-size: 16px;
                }}
                .content {{ 
                    padding: 30px; 
                    line-height: 1.7;
                }}
                .receipt-data {{ 
                    background-color: #f8f9ff; 
                    border-left: 4px solid #28a745; 
                    padding: 20px; 
                    margin: 20px 0; 
                    border-radius: 0 8px 8px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .receipt-data h3 {{
                    color: #2c3e50;
                    margin-top: 0;
                    font-size: 20px;
                }}
                .receipt-data p {{
                    margin: 10px 0;
                }}
                .receipt-data ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .receipt-data li {{
                    margin: 5px 0;
                }}
                .highlight {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #ffc107;
                    margin: 15px 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💰 Dados de Recibo de IA</h1>
                    <p>Dados extraídos automaticamente pelo sistema de automação</p>
                </div>
                <div class="content">
                    {html_content}
                </div>
                <div class="footer">
                    <p>Enviado automaticamente pelo Sistema de Automação de Recibos de IA</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_receipt_data_text(self, receipt_data: str) -> str:
        """
        Formata dados de recibo em texto simples.
        
        Args:
            receipt_data: Dados extraídos do recibo
            
        Returns:
            Texto formatado
        """
        return f"""
DADOS DE RECIBO DE IA
====================

Documento gerado automaticamente pelo sistema de automação

{receipt_data}

---
Enviado automaticamente pelo Sistema de Automação de Recibos de IA
        """.strip()
    
    def _json_to_html_receipt(self, data: dict) -> str:
        """
        Converte dados JSON de recibo para HTML.
        
        Args:
            data: Dados do recibo em formato JSON
            
        Returns:
            HTML formatado
        """
        html = "<div class='receipt-data'>"
        
        if 'provider' in data:
            html += f"<h3>🏢 Provedor: {data['provider']}</h3>"
        
        if 'amount' in data and data['amount']:
            currency = data.get('currency', 'USD')
            html += f"<p><strong>💰 Valor:</strong> {data['amount']} {currency}</p>"
        
        if 'date' in data and data['date']:
            html += f"<p><strong>📅 Data:</strong> {data['date']}</p>"
        
        if 'description' in data and data['description']:
            html += f"<p><strong>📝 Descrição:</strong> {data['description']}</p>"
        
        if 'invoice_number' in data and data['invoice_number']:
            html += f"<p><strong>🔢 Número da Fatura:</strong> {data['invoice_number']}</p>"
        
        if 'vendor' in data and data['vendor']:
            html += f"<p><strong>🏪 Fornecedor:</strong> {data['vendor']}</p>"
        
        if 'confidence_score' in data and data['confidence_score']:
            score = data['confidence_score']
            color = "green" if score > 80 else "orange" if score > 60 else "red"
            html += f"<p><strong>🎯 Confiança:</strong> <span style='color: {color}'>{score}%</span></p>"
        
        html += "</div>"
        return html
    
    def _format_user_stories_html(self, user_stories: str) -> str:
        """
        Formata Histórias de Usuário em HTML.
        
        Args:
            user_stories: Texto das Histórias de Usuário
            
        Returns:
            HTML formatado
        """
        # Converter markdown para HTML
        html_content = self._markdown_to_html(user_stories)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Histórias de Usuário</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f8f9fa;
                    color: #333;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                    color: white; 
                    padding: 30px; 
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 600;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    opacity: 0.9;
                    font-size: 16px;
                }}
                .content {{ 
                    padding: 30px; 
                    line-height: 1.7;
                }}
                .user-story {{ 
                    background-color: #f8f9ff; 
                    border-left: 4px solid #4facfe; 
                    padding: 20px; 
                    margin: 20px 0; 
                    border-radius: 0 8px 8px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }}
                .user-story h3 {{
                    color: #2c3e50;
                    margin-top: 0;
                    font-size: 20px;
                }}
                .user-story p {{
                    margin: 10px 0;
                }}
                .user-story ul {{
                    margin: 10px 0;
                    padding-left: 20px;
                }}
                .user-story li {{
                    margin: 5px 0;
                }}
                .criteria {{
                    background-color: #e8f5e8;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 10px 0;
                }}
                .criteria h4 {{
                    margin-top: 0;
                    color: #27ae60;
                }}
                .highlight {{
                    background-color: #fff3cd;
                    padding: 15px;
                    border-radius: 5px;
                    border-left: 4px solid #ffc107;
                    margin: 15px 0;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Histórias de Usuário</h1>
                    <p>Documento gerado automaticamente pelo sistema de automação</p>
                </div>
                <div class="content">
                    {html_content}
                </div>
                <div class="footer">
                    <p>Enviado automaticamente pelo Sistema de Automação de Histórias de Usuário</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _format_user_stories_text(self, user_stories: str) -> str:
        """
        Formata Histórias de Usuário em texto simples.
        
        Args:
            user_stories: Texto das Histórias de Usuário
            
        Returns:
            Texto formatado
        """
        # Converter markdown para texto limpo
        clean_text = self._markdown_to_text(user_stories)
        
        return f"""
HISTÓRIAS DE USUÁRIO
====================

Documento gerado automaticamente pelo sistema de automação

{clean_text}

---
Enviado automaticamente pelo Sistema de Automação de Histórias de Usuário
        """.strip()
    
    def _markdown_to_html(self, text: str) -> str:
        """
        Converte markdown básico para HTML.
        
        Args:
            text: Texto em markdown
            
        Returns:
            HTML convertido
        """
        import re
        
        # Converter títulos
        text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
        text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
        text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
        
        # Converter negrito
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        
        # Converter itálico
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        
        # Converter listas
        lines = text.split('\n')
        html_lines = []
        in_list = False
        
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                content = re.sub(r'^\s*[-*+]\s+', '', line)
                html_lines.append(f'<li>{content}</li>')
            elif re.match(r'^\s*\d+\.\s+', line):
                if not in_list:
                    html_lines.append('<ol>')
                    in_list = True
                content = re.sub(r'^\s*\d+\.\s+', '', line)
                html_lines.append(f'<li>{content}</li>')
            else:
                if in_list:
                    html_lines.append('</ul>' if 'ol>' not in ''.join(html_lines[-3:]) else '</ol>')
                    in_list = False
                if line.strip():
                    html_lines.append(f'<p>{line}</p>')
                else:
                    html_lines.append('<br>')
        
        if in_list:
            html_lines.append('</ul>')
        
        return '\n'.join(html_lines)
    
    def _markdown_to_text(self, text: str) -> str:
        """
        Converte markdown para texto limpo.
        
        Args:
            text: Texto em markdown
            
        Returns:
            Texto limpo
        """
        import re
        
        # Remover títulos (###, ##, #)
        text = re.sub(r'^#{1,3}\s+', '', text, flags=re.MULTILINE)
        
        # Remover negrito e itálico
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        
        # Converter listas para texto simples
        lines = text.split('\n')
        clean_lines = []
        
        for line in lines:
            if re.match(r'^\s*[-*+]\s+', line):
                # Lista com marcadores
                content = re.sub(r'^\s*[-*+]\s+', '• ', line)
                clean_lines.append(content)
            elif re.match(r'^\s*\d+\.\s+', line):
                # Lista numerada
                content = re.sub(r'^\s*\d+\.\s+', '', line)
                clean_lines.append(f"  {content}")
            else:
                clean_lines.append(line)
        
        return '\n'.join(clean_lines)
    
    def send_receipt_data_with_attachment(
        self,
        to_emails: List[str],
        receipt_data: str,
        attachment_path: str,
        attachment_filename: str = None,
        body_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Envia e-mail com dados de recibo e anexo.
        
        Args:
            to_emails: Lista de e-mails destinatários
            receipt_data: Dados extraídos do recibo
            attachment_path: Caminho para o arquivo anexo
            attachment_filename: Nome do arquivo anexo (opcional)
            
        Returns:
            Dicionário com resultado do envio
        """
        try:
            if not os.path.exists(attachment_path):
                return {
                    "success": False,
                    "error": "Arquivo anexo não encontrado"
                }
            
            # Ler conteúdo do anexo
            with open(attachment_path, 'rb') as f:
                attachment_content = f.read()
            
            # Determinar tipo MIME do anexo
            import mimetypes
            mime_type, _ = mimetypes.guess_type(attachment_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Preparar anexo
            attachment = {
                'filename': attachment_filename or os.path.basename(attachment_path),
                'content': attachment_content,
                'content_type': mime_type
            }
            
            # Preparar corpo do e-mail
            subject = "Dados de Recibo de IA - Documento Anexo"
            if body_format.lower() == "html":
                body = self._format_receipt_data_html(receipt_data)
                is_html = True
            else:
                body = self._format_receipt_data_text(receipt_data)
                is_html = False
            
            # Enviar e-mail com anexo
            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                is_html=is_html,
                attachments=[attachment]
            )
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao enviar e-mail com anexo: {str(e)}"
            }
    
    def send_user_stories_with_attachment(
        self,
        to_emails: List[str],
        user_stories: str,
        attachment_path: str,
        attachment_filename: str = None,
        body_format: str = "html"
    ) -> Dict[str, Any]:
        """
        Envia e-mail com Histórias de Usuário e anexo.
        
        Args:
            to_emails: Lista de e-mails destinatários
            user_stories: Texto das Histórias de Usuário
            attachment_path: Caminho para o arquivo anexo
            attachment_filename: Nome do arquivo anexo (opcional)
            
        Returns:
            Dicionário com resultado do envio
        """
        try:
            if not os.path.exists(attachment_path):
                return {
                    "success": False,
                    "error": "Arquivo anexo não encontrado"
                }
            
            # Ler conteúdo do anexo
            with open(attachment_path, 'rb') as f:
                attachment_content = f.read()
            
            # Determinar tipo MIME do anexo
            import mimetypes
            mime_type, _ = mimetypes.guess_type(attachment_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Preparar anexo
            attachment = {
                'filename': attachment_filename or os.path.basename(attachment_path),
                'content': attachment_content,
                'content_type': mime_type
            }
            
            # Preparar corpo do e-mail
            subject = "Histórias de Usuário - Documento Anexo"
            if body_format.lower() == "html":
                body = self._format_user_stories_html(user_stories)
                is_html = True
            else:
                body = self._format_user_stories_text(user_stories)
                is_html = False
            
            # Enviar e-mail com anexo
            return self.send_email(
                to_emails=to_emails,
                subject=subject,
                body=body,
                is_html=is_html,
                attachments=[attachment]
            )
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro ao enviar e-mail com anexo: {str(e)}"
            }
