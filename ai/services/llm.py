"""LLM Service - Text generation using OpenAI."""
import os
import logging
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


DEFAULT_SYSTEM_PROMPT = """Bạn là chuyên gia pháp luật chứng khoán Việt Nam.

Nhiệm vụ: Trả lời câu hỏi dựa trên tài liệu được cung cấp.

Format câu trả lời:
1. Tóm tắt câu trả lời chính
2. Chi tiết quy định (nếu có)
3. Lưu ý quan trọng (nếu có)
4. Nguồn tham khảo

Nếu không có đủ thông tin, nói rõ và đề xuất nguồn tra cứu."""


CHAT_SYSTEM_PROMPT = "Bạn là trợ lý pháp luật chứng khoán Việt Nam. Trả lời thân thiện, ngắn gọn."


class LLMService:
    """Service for LLM text generation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", model)
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for LLM service")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate(
        self,
        query: str,
        context: str,
        system_prompt: Optional[str] = None
    ) -> dict:
        """
        Generate answer using LLM.
        
        Input: query, context, optional system_prompt
        Output: dict with answer, model, token counts
        """
        try:
            prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
            
            user_content = f"""Câu hỏi: {query}

Tài liệu tham khảo:
{context}

Hãy trả lời câu hỏi dựa trên tài liệu trên."""
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            usage = response.usage
            
            return {
                "answer": response.choices[0].message.content,
                "model": self.model,
                "input_tokens": usage.prompt_tokens if usage else None,
                "output_tokens": usage.completion_tokens if usage else None
            }
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                "answer": f"Không thể tạo câu trả lời. Lỗi: {str(e)}",
                "model": self.model,
                "input_tokens": None,
                "output_tokens": None
            }
    
    async def chat(self, query: str) -> str:
        """
        Simple chat response for general queries.
        
        Input: query string
        Output: response string
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat response failed: {e}")
            return "Xin lỗi, tôi không thể xử lý yêu cầu lúc này."


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
