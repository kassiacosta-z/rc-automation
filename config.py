"""
Configurações da aplicação de automação de Recibos de IA.
Todas as configurações sensíveis são carregadas de variáveis de ambiente.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
loaded = load_dotenv()
if loaded:
    print(".env carregado")
else:
    print(".env não encontrado; usando variáveis de ambiente do sistema")


class Config:
    """Configurações da aplicação."""
    
    # Configurações do Flask
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    HOST: str = os.getenv('FLASK_HOST', '127.0.0.1')
    PORT: int = int(os.getenv('FLASK_PORT', '5000'))
    
    # Configurações das LLMs
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    ZELLO_API_KEY: Optional[str] = os.getenv('ZELLO_API_KEY')
    ZELLO_BASE_URL: str = os.getenv('ZELLO_BASE_URL', 'https://api.zello.com')
    
    # APIs de faturamento
    ANTHROPIC_ADMIN_API_KEY: Optional[str] = os.getenv('ANTHROPIC_ADMIN_API_KEY')
    CURSOR_ADMIN_API_KEY: Optional[str] = os.getenv('CURSOR_ADMIN_API_KEY')
    
    # Configurações de e-mail
    SMTP_SERVER: str = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    SMTP_USERNAME: Optional[str] = os.getenv('EMAIL_USERNAME')
    SMTP_PASSWORD: Optional[str] = os.getenv('EMAIL_PASSWORD')
    EMAIL_FROM: Optional[str] = os.getenv('EMAIL_FROM', os.getenv('EMAIL_USERNAME'))
    
    # Configurações de upload
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', '16777216'))  # 16MB
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', 'uploads')
    ALLOWED_EXTENSIONS: set = {'txt', 'pdf', 'doc', 'docx', 'md'}

    # Banco de dados (SQLite por padrão para desenvolvimento)
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    
    # Configurações do repositório de recibos
    RECEIPTS_REPO_PATH: Optional[str] = os.getenv('RECEIPTS_REPO_PATH')
    MONITOR_INTERVAL_SECONDS: int = int(os.getenv('MONITOR_INTERVAL_SECONDS', '60'))
    
    # Configurações de monitoramento
    GMAIL_MONITORED_EMAIL: Optional[str] = os.getenv('GMAIL_MONITORED_EMAIL')
    REPORTS_EMAIL: Optional[str] = os.getenv('REPORTS_EMAIL')
    
    # Configurações de agendamento
    MONITOR_PEAK_DAYS: str = os.getenv('MONITOR_PEAK_DAYS', '15,16,17,18')
    MONITOR_PEAK_INTERVAL_HOURS: int = int(os.getenv('MONITOR_PEAK_INTERVAL_HOURS', '2'))
    MONITOR_NORMAL_INTERVAL_HOURS: int = int(os.getenv('MONITOR_NORMAL_INTERVAL_HOURS', '12'))

    # Google APIs
    GOOGLE_CREDENTIALS_JSON: Optional[str] = os.getenv('GOOGLE_CREDENTIALS_JSON')  # caminho do JSON da service account
    GMAIL_DELEGATED_USER: Optional[str] = os.getenv('GMAIL_DELEGATED_USER')  # e-mail a ser delegado (DWD)
    GDRIVE_ROOT_FOLDER_ID: Optional[str] = os.getenv('GDRIVE_ROOT_FOLDER_ID')  # pasta raiz onde salvar
    
    @classmethod
    def validate_config(cls) -> list[str]:
        """
        Valida se todas as configurações necessárias estão definidas.
        
        Returns:
            Lista de mensagens de erro se houver configurações faltando.
        """
        errors = []
        
        if not cls.OPENAI_API_KEY and not cls.ZELLO_API_KEY:
            errors.append("Pelo menos uma chave de API (OPENAI_API_KEY ou ZELLO_API_KEY) deve ser definida")
        
        if not cls.GMAIL_MONITORED_EMAIL:
            errors.append("GMAIL_MONITORED_EMAIL deve ser definido para monitoramento de recibos")
        
        if not cls.REPORTS_EMAIL:
            errors.append("REPORTS_EMAIL deve ser definido para envio de relatórios")
        
        if not cls.SMTP_USERNAME or not cls.SMTP_PASSWORD:
            errors.append("Configurações de SMTP (SMTP_USERNAME e SMTP_PASSWORD) são obrigatórias")
        
        if not cls.EMAIL_FROM:
            errors.append("EMAIL_FROM deve ser definido")
        
        return errors


# Instância global de configuração
config = Config()
