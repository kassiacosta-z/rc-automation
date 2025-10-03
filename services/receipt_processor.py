"""
Serviço para processamento e extração de dados de recibos de IA com auto-correção.
"""

import json
import re
from typing import Dict, Any, List, Tuple, Optional
from services.llm_service import LLMService
from prompts.receipt_prompts import ReceiptPrompts


class ReceiptProcessor:
    """Serviço para processamento e extração de dados de recibos de IA."""
    
    def __init__(self, llm_service: LLMService):
        """
        Inicializa o processador de recibos.
        
        Args:
            llm_service: Instância do serviço de LLM
        """
        self.llm_service = llm_service
        self.prompts = ReceiptPrompts()
    
    def extract_receipt_data(self, receipt_text: str, provider: str = "auto", max_attempts: int = 3) -> Dict[str, Any]:
        """
        Extrai dados de recibo com auto-correção baseada em validação.
        
        Args:
            receipt_text: Texto do recibo para processar
            provider: Provedor da LLM ('auto', 'openai' ou 'zello')
            max_attempts: Número máximo de tentativas
            
        Returns:
            Dicionário com resultado da extração
        """
        attempts = []
        
        for attempt in range(max_attempts):
            # Gerar extração
            generation_result = self._generate_extraction(receipt_text, provider)
            if not generation_result["success"]:
                return generation_result
            
            # Validar extração
            validation_result = self._validate_extraction(
                generation_result["content"], 
                receipt_text, 
                provider
            )
            if not validation_result["success"]:
                return validation_result
            
            # Registrar tentativa
            attempts.append({
                "attempt": attempt + 1,
                "generation": generation_result,
                "validation": validation_result
            })
            
            # Se aprovado, retornar resultado
            if validation_result["is_approved"]:
                return {
                    "success": True,
                    "extracted_data": self._parse_extracted_json(generation_result["content"]),
                    "raw_response": generation_result["content"],
                    "provider": provider,
                    "attempts": attempts,
                    "final_validation": validation_result,
                    "auto_correction_used": attempt > 0
                }
            
            # Se não aprovado e ainda há tentativas, usar feedback para correção
            if attempt < max_attempts - 1:
                feedback = validation_result["feedback"]
                receipt_text = self._update_prompt_with_feedback(receipt_text, feedback)
        
        # Se chegou aqui, todas as tentativas falharam
        return {
            "success": False,
            "error": f"Não foi possível extrair dados adequados após {max_attempts} tentativas",
            "provider": provider,
            "attempts": attempts,
            "final_validation": validation_result
        }
    
    def _generate_extraction(self, receipt_text: str, provider: str) -> Dict[str, Any]:
        """
        Gera extração de dados usando LLM.
        
        Args:
            receipt_text: Texto do recibo
            provider: Provedor da LLM
            
        Returns:
            Dicionário com resultado da geração
        """
        try:
            # Gerar prompt para extração
            prompt = self.prompts.extract_receipt_data(receipt_text)
            
            # Preparar mensagens para a LLM
            messages = [
                {
                    "role": "system",
                    "content": "Você é um especialista em análise de recibos de provedores de IA. Extraia os dados financeiros de forma estruturada e precisa seguindo rigorosamente as instruções fornecidas."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Resolver provider com fallback automático
            provider_call = provider if provider in ["openai", "zello"] else "auto"
            
            # Chamar a LLM
            response = self.llm_service.get_completion(provider_call, messages)
            
            return {
                "success": True,
                "content": response,
                "provider": provider_call,
                "prompt_used": prompt
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro na extração: {str(e)}",
                "provider": provider
            }
    
    def _validate_extraction(self, extracted_json: str, original_text: str, provider: str) -> Dict[str, Any]:
        """
        Valida dados extraídos usando LLM.
        
        Args:
            extracted_json: JSON com dados extraídos
            original_text: Texto original do recibo
            provider: Provedor da LLM
            
        Returns:
            Dicionário com resultado da validação
        """
        try:
            # Gerar prompt para validação
            prompt = self.prompts.analyze_receipt_quality(extracted_json)
            
            # Preparar mensagens para a LLM
            messages = [
                {
                    "role": "system",
                    "content": "Você é um validador especializado em dados de recibos de IA. Analise rigorosamente a qualidade da extração e forneça feedback detalhado."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Resolver provider com fallback automático
            provider_call = provider if provider in ["openai", "zello"] else "auto"
            
            # Chamar a LLM
            response = self.llm_service.get_completion(provider_call, messages)
            
            # Analisar a resposta para determinar se foi aprovada
            is_approved, feedback = self._analyze_validation_response(response)
            
            return {
                "success": True,
                "is_approved": is_approved,
                "feedback": feedback,
                "full_response": response,
                "provider": provider_call
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro na validação: {str(e)}",
                "provider": provider
            }
    
    def _analyze_validation_response(self, response: str) -> Tuple[bool, str]:
        """
        Analisa a resposta de validação para determinar aprovação.
        
        Args:
            response: Resposta da LLM sobre validação
            
        Returns:
            Tupla com (aprovado, feedback)
        """
        # Palavras-chave que indicam aprovação
        approval_keywords = [
            "aprovado", "aprovada", "aprovadas",
            "adequado", "adequada", "adequadas",
            "correto", "correta", "corretas",
            "bom", "boa", "boas",
            "satisfatório", "satisfatória", "satisfatórias",
            "aceitável", "aceitáveis",
            "válido", "válida", "válidas",
            "completo", "completa", "completas",
            "preciso", "precisa", "precisas"
        ]
        
        # Palavras-chave que indicam reprovação
        rejection_keywords = [
            "reprovado", "reprovada", "reprovadas",
            "inadequado", "inadequada", "inadequadas",
            "incorreto", "incorreta", "incorretas",
            "ruim", "ruins",
            "insatisfatório", "insatisfatória", "insatisfatórias",
            "inaceitável", "inaceitáveis",
            "inválido", "inválida", "inválidas",
            "problema", "problemas",
            "erro", "erros",
            "falta", "faltam",
            "melhorar", "melhorias",
            "incompleto", "incompleta", "incompletas",
            "impreciso", "imprecisa", "imprecisas"
        ]
        
        response_lower = response.lower()
        
        # Contar ocorrências de palavras de aprovação e reprovação
        approval_count = sum(1 for keyword in approval_keywords if keyword in response_lower)
        rejection_count = sum(1 for keyword in rejection_keywords if keyword in response_lower)
        
        # Determinar aprovação baseada na contagem e contexto
        if rejection_count > approval_count:
            is_approved = False
        elif approval_count > rejection_count:
            is_approved = True
        else:
            # Em caso de empate, verificar se há sugestões de melhoria
            improvement_indicators = [
                "sugestão", "sugestões", "recomendação", "recomendações",
                "melhorar", "refinar", "ajustar", "corrigir"
            ]
            has_improvements = any(indicator in response_lower for indicator in improvement_indicators)
            is_approved = not has_improvements
        
        # Extrair feedback específico
        feedback = self._extract_feedback(response, is_approved)
        
        return is_approved, feedback
    
    def _extract_feedback(self, response: str, is_approved: bool) -> str:
        """
        Extrai feedback específico da resposta de validação.
        
        Args:
            response: Resposta completa da LLM
            is_approved: Se foi aprovado ou não
            
        Returns:
            Feedback específico extraído
        """
        if is_approved:
            # Procurar por elogios e pontos positivos
            positive_patterns = [
                r"(?:bom|boa|boas|excelente|ótimo|ótima|ótimas).*?(?:\n|$)",
                r"(?:adequado|adequada|adequadas|correto|correta|corretas).*?(?:\n|$)",
                r"(?:aprovado|aprovada|aprovadas|aceitável|aceitáveis).*?(?:\n|$)"
            ]
        else:
            # Procurar por problemas e sugestões de melhoria
            positive_patterns = [
                r"(?:problema|problemas|erro|erros).*?(?:\n|$)",
                r"(?:melhorar|refinar|ajustar|corrigir).*?(?:\n|$)",
                r"(?:sugestão|sugestões|recomendação|recomendações).*?(?:\n|$)"
            ]
        
        feedback_parts = []
        for pattern in positive_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE | re.MULTILINE)
            feedback_parts.extend(matches)
        
        if feedback_parts:
            return " ".join(feedback_parts[:3])  # Limitar a 3 partes
        else:
            # Fallback: retornar as primeiras 200 caracteres da resposta
            return response[:200] + "..." if len(response) > 200 else response
    
    def _update_prompt_with_feedback(self, receipt_text: str, feedback: str) -> str:
        """
        Atualiza o texto do recibo com feedback para correção.
        
        Args:
            receipt_text: Texto original do recibo
            feedback: Feedback da validação
            
        Returns:
            Texto atualizado com feedback
        """
        return f"{receipt_text}\n\nFEEDBACK PARA CORREÇÃO:\n{feedback}"
    
    def _parse_extracted_json(self, json_string: str) -> Dict[str, Any]:
        """
        Faz parse do JSON extraído, tratando erros de formatação.
        
        Args:
            json_string: String JSON extraída
            
        Returns:
            Dicionário com dados parseados
        """
        try:
            # Tentar parse direto
            return json.loads(json_string)
        except json.JSONDecodeError:
            # Tentar extrair JSON do texto usando regex
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, json_string, re.DOTALL)
            
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    pass
            
            # Se não conseguir parsear, retornar estrutura vazia
            return {
                "plataforma": None,
                "valor": None,
                "moeda": None,
                "data_emissao": None,
                "numero_recibo": None,
                "confianca": 0,
                "fonte_dados": json_string[:200] if json_string else ""
            }
    
    def process_email_receipt(self, email_content: str, provider: str = "auto") -> Dict[str, Any]:
        """
        Processa um recibo completo de email.
        
        Args:
            email_content: Conteúdo completo do email
            provider: Provedor da LLM
            
        Returns:
            Dicionário com resultado do processamento
        """
        try:
            # Extrair texto do recibo do email
            receipt_text = self._extract_receipt_from_email(email_content)
            
            if not receipt_text:
                return {
                    "success": False,
                    "error": "Não foi possível extrair texto do recibo do email",
                    "provider": provider
                }
            
            # Processar o recibo extraído
            result = self.extract_receipt_data(receipt_text, provider)
            
            # Adicionar informações do email ao resultado
            if result["success"]:
                result["email_processed"] = True
                result["receipt_text_length"] = len(receipt_text)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Erro no processamento do email: {str(e)}",
                "provider": provider
            }
    
    def _extract_receipt_from_email(self, email_content: str) -> str:
        """
        Extrai texto do recibo de um email.
        
        Args:
            email_content: Conteúdo completo do email
            
        Returns:
            Texto do recibo extraído
        """
        # Padrões comuns para identificar recibos em emails
        receipt_patterns = [
            r"(?:invoice|recibo|fatura|bill|receipt).*?(?=\n\n|\n[A-Z]|$)",
            r"(?:amount|valor|total|price|preço).*?(?=\n\n|\n[A-Z]|$)",
            r"(?:date|data).*?(?=\n\n|\n[A-Z]|$)",
            r"(?:openai|anthropic|cursor|manus|n8n).*?(?=\n\n|\n[A-Z]|$)"
        ]
        
        # Procurar por padrões de recibo
        for pattern in receipt_patterns:
            matches = re.findall(pattern, email_content, re.IGNORECASE | re.DOTALL)
            if matches:
                return matches[0].strip()
        
        # Se não encontrar padrões específicos, retornar o conteúdo completo
        return email_content.strip()
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas do processamento.
        
        Returns:
            Dicionário com estatísticas
        """
        return {
            "service": "ReceiptProcessor",
            "llm_service_available": self.llm_service is not None,
            "prompts_available": self.prompts is not None,
            "supported_providers": ["auto", "openai", "zello"]
        }
