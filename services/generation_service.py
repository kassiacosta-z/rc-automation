"""
Serviço para geração e validação de Histórias de Usuário.
"""

import json
import re
from typing import Dict, Any, List, Tuple
from services.llm_service import LLMService
from prompts.receipt_prompts import ReceiptPrompts


class GenerationService:
    """Serviço para geração e validação de Histórias de Usuário."""
    
    def __init__(self, llm_service: LLMService):
        """
        Inicializa o serviço de geração.
        
        Args:
            llm_service: Instância do serviço de LLM
        """
        self.llm_service = llm_service
        self.prompts = ReceiptPrompts()
    
    def run_generation(self, text: str, provider: str = "openai") -> Dict[str, Any]:
        """
        Gera Histórias de Usuário a partir de um texto.
        
        Args:
            text: Texto de entrada para processar
            provider: Provedor da LLM ('openai' ou 'zello')
            
        Returns:
            Dicionário com resultado da geração
        """
        try:
            # Gerar prompt para criação de Histórias de Usuário
            prompt = self.prompts.generate_user_stories_from_requirements(text)
            
            # Preparar mensagens para a LLM
            messages = [
                {
                    "role": "system",
                    "content": "Você é um especialista em análise de requisitos e criação de Histórias de Usuário. Siga rigorosamente as instruções fornecidas."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Resolver provider com fallback automático
            provider_call = provider if provider == "openai" else "auto"
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
                "error": f"Erro na geração: {str(e)}",
                "provider": provider
            }
    
    def run_validation(self, user_stories: str, provider: str = "openai") -> Dict[str, Any]:
        """
        Valida as Histórias de Usuário geradas.
        
        Args:
            user_stories: Texto das Histórias de Usuário
            provider: Provedor da LLM ('openai' ou 'zello')
            
        Returns:
            Dicionário com resultado da validação
        """
        try:
            # Gerar prompt para validação
            prompt = self.prompts.analyze_existing_user_stories(user_stories)
            
            # Preparar mensagens para a LLM
            messages = [
                {
                    "role": "system",
                    "content": "Você é um especialista em validação de Histórias de Usuário. Analise rigorosamente e forneça feedback detalhado."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # Resolver provider com fallback automático
            provider_call = provider if provider == "openai" else "auto"
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
            "válido", "válida", "válidas"
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
            "melhorar", "melhorias"
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
    
    def generate_with_auto_correction(self, text: str, provider: str = "openai", max_attempts: int = 3) -> Dict[str, Any]:
        """
        Gera Histórias de Usuário com auto-correção baseada em validação.
        
        Args:
            text: Texto de entrada para processar
            provider: Provedor da LLM ('openai' ou 'zello')
            max_attempts: Número máximo de tentativas
            
        Returns:
            Dicionário com resultado final
        """
        attempts = []
        
        for attempt in range(max_attempts):
            # Gerar Histórias de Usuário
            generation_result = self.run_generation(text, provider)
            if not generation_result["success"]:
                return generation_result
            
            # Validar resultado
            validation_result = self.run_validation(generation_result["content"], provider)
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
                    "content": generation_result["content"],
                    "provider": provider,
                    "attempts": attempts,
                    "final_validation": validation_result,
                    "auto_correction_used": attempt > 0
                }
            
            # Se não aprovado e ainda há tentativas, usar feedback para correção
            if attempt < max_attempts - 1:
                feedback = validation_result["feedback"]
                text = f"{text}\n\nFeedback para correção: {feedback}"
        
        # Se chegou aqui, todas as tentativas falharam
        return {
            "success": False,
            "error": f"Não foi possível gerar Histórias de Usuário adequadas após {max_attempts} tentativas",
            "provider": provider,
            "attempts": attempts,
            "final_validation": validation_result
        }
