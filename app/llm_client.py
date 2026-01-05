"""
Cliente LLM para processamento de linguagem natural
"""

import asyncio
from typing import Optional

import structlog
from openai import AsyncOpenAI

from config import settings

logger = structlog.get_logger(__name__)


class LLMClient:
    """
    Cliente para geração de respostas usando LLM (OpenAI GPT)

    Processa o contexto da conversa e gera respostas apropriadas
    para atendimento telefônico.
    """

    def __init__(self, system_prompt: str):
        """
        Args:
            system_prompt: Prompt de sistema que define o comportamento do assistente
        """
        self.system_prompt = system_prompt
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.temperature = settings.LLM_TEMPERATURE

    async def generate_response(
        self,
        user_input: str,
        conversation_history: list[dict],
        context: Optional[dict] = None
    ) -> str:
        """
        Gera resposta para a entrada do usuário

        Args:
            user_input: Texto do usuário
            conversation_history: Histórico da conversa
            context: Contexto adicional (opcional)

        Returns:
            Resposta gerada pelo LLM
        """
        try:
            # Montar mensagens
            messages = [
                {"role": "system", "content": self._build_system_prompt(context)}
            ]

            # Adicionar histórico (limitado para não exceder contexto)
            # Manter últimas 10 mensagens para contexto
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history

            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            logger.debug(
                "Gerando resposta LLM",
                model=self.model,
                messages_count=len(messages)
            )

            # Chamar API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            # Extrair resposta
            answer = response.choices[0].message.content

            if not answer:
                return "Desculpe, não consegui processar sua solicitação."

            return answer.strip()

        except Exception as e:
            logger.exception("Erro ao gerar resposta LLM", error=str(e))
            return "Desculpe, estou com dificuldades técnicas no momento."

    def _build_system_prompt(self, context: Optional[dict] = None) -> str:
        """Constrói prompt de sistema com contexto adicional"""
        prompt = self.system_prompt

        if context:
            prompt += "\n\nContexto adicional:"
            for key, value in context.items():
                prompt += f"\n- {key}: {value}"

        # Adicionar instruções para telefonia
        prompt += """

IMPORTANTE - Regras para respostas telefônicas:
1. Mantenha respostas CURTAS (máximo 2-3 frases)
2. Use linguagem NATURAL e conversacional
3. Evite listas, bullets ou formatação complexa
4. Não use emojis ou caracteres especiais
5. Seja direto e objetivo
6. Se precisar de informação, faça UMA pergunta por vez
7. Confirme informações importantes repetindo-as"""

        return prompt

    async def analyze_intent(self, text: str) -> dict:
        """
        Analisa a intenção do usuário

        Returns:
            Dict com 'intent', 'confidence' e 'entities'
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Analise a intenção do usuário e retorne JSON:
{
    "intent": "nome_da_intencao",
    "confidence": 0.0 a 1.0,
    "entities": {"entidade": "valor"}
}

Intenções possíveis: saudacao, despedida, pergunta, reclamacao, solicitacao, confirmacao, negacao, outros"""
                    },
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            import json
            return json.loads(response.choices[0].message.content)

        except Exception as e:
            logger.exception("Erro ao analisar intenção", error=str(e))
            return {"intent": "outros", "confidence": 0.0, "entities": {}}

    async def summarize_conversation(self, conversation_history: list[dict]) -> str:
        """Gera resumo da conversa para logs/CRM"""
        try:
            # Formatar histórico
            formatted = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}"
                for msg in conversation_history
            ])

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Resuma a conversa telefônica abaixo em 2-3 frases, destacando o motivo do contato e a resolução."
                    },
                    {"role": "user", "content": formatted}
                ],
                max_tokens=200,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.exception("Erro ao resumir conversa", error=str(e))
            return "Resumo não disponível"
