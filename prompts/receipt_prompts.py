"""
Prompts para extração e validação de dados de recibos.
"""

from typing import Dict, Any


class ReceiptPrompts:
    """Prompts para processamento de recibos de IA."""
    
    @staticmethod
    def get_extractor_prompt() -> str:
        """Prompt para extrair dados estruturados de recibos."""
        return """
        Extraia os seguintes dados do texto do recibo em formato JSON:
        {
            "plataforma": "nome da plataforma (OpenAI, Anthropic, Cursor, etc.)",
            "valor": valor numérico (apenas números),
            "moeda": "código da moeda (BRL, USD, EUR)",
            "data_emissao": "data no formato DD-MM-YYYY",
            "numero_recibo": "número do recibo ou invoice"
        }
        
        Regras:
        - Se não encontrar um campo, use null
        - Valor deve ser apenas números (ex: 550.00, não R$ 550,00)
        - Data deve estar no formato DD-MM-YYYY
        - Plataforma deve ser o nome da empresa (não o domínio)
        """
    
    @staticmethod
    def get_validator_prompt() -> str:
        """Prompt para validar dados extraídos."""
        return """
        Valide os dados extraídos do recibo:
        1. Verifique se todos os campos obrigatórios estão preenchidos
        2. Confirme se os valores são consistentes com o texto original
        3. Verifique se o formato está correto
        
        Retorne um JSON com:
        {
            "score": número de 0 a 100,
            "aprovado": true/false,
            "feedback": "sugestões de melhoria se necessário"
        }
        """
