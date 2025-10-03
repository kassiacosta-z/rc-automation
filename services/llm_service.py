"""
Serviço para comunicação com LLMs (OpenAI e Zello MIND).
"""

from typing import Dict, Any, Optional
import requests
import json
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Serviço unificado para comunicação com LLMs."""
    
    def __init__(self):
        self.openai_api_key = None
        self.zello_api_key = None
        self.zello_base_url = "https://api.zello.com"
        
        # Carregar chaves do ambiente
        import os
        from config import config
        self.openai_api_key = config.OPENAI_API_KEY
        self.zello_api_key = config.ZELLO_API_KEY
        self.zello_base_url = config.ZELLO_BASE_URL

    def generate_text(self, prompt: str, model: str = "zello", max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Gera texto usando o modelo especificado.
        
        Args:
            prompt: Texto de entrada
            model: "openai" ou "zello"
            max_tokens: Número máximo de tokens
            
        Returns:
            Dict com 'success', 'text' e 'error' (se houver)
        """
        if model.lower() == "zello":
            return self._call_zello(prompt, max_tokens)
        elif model.lower() == "openai":
            return self._call_openai(prompt, max_tokens)
        else:
            return {"success": False, "error": f"Modelo não suportado: {model}"}

    def _call_zello(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Chama a API do Zello MIND."""
        if not self.zello_api_key:
            return {"success": False, "error": "ZELLO_API_KEY não configurada"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.zello_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.zello_base_url}/v1/generate",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "text": result.get("text", ""),
                    "usage": result.get("usage", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro Zello API: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao chamar Zello API: {e}")
            return {"success": False, "error": str(e)}

    def _call_openai(self, prompt: str, max_tokens: int) -> Dict[str, Any]:
        """Chama a API do OpenAI."""
        if not self.openai_api_key:
            return {"success": False, "error": "OPENAI_API_KEY não configurada"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "text": text,
                    "usage": result.get("usage", {})
                }
            else:
                return {
                    "success": False,
                    "error": f"Erro OpenAI API: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI API: {e}")
            return {"success": False, "error": str(e)}
