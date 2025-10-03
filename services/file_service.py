"""
Serviço para manipulação de arquivos.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FileService:
    """Serviço para manipulação de arquivos."""
    
    def __init__(self):
        self.upload_folder = "uploads"
        os.makedirs(self.upload_folder, exist_ok=True)

    def save_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Salva um arquivo."""
        try:
            file_path = os.path.join(self.upload_folder, filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            return {"success": True, "file_path": file_path}
        except Exception as e:
            logger.error(f"Erro ao salvar arquivo: {e}")
            return {"success": False, "error": str(e)}

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Lê um arquivo."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return {"success": True, "content": content}
        except Exception as e:
            logger.error(f"Erro ao ler arquivo: {e}")
            return {"success": False, "error": str(e)}
