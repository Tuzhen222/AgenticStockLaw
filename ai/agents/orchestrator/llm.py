"""
LLM Client - Handles LLM calls for answer generation.

Supports OpenAI GPT-4 and Google Gemini models.
"""
import os
import logging
from typing import Optional

from openai import AsyncOpenAI
from ai.utils.api_key_manager import get_api_key_manager

logger = logging.getLogger(__name__)


ANSWER_SYSTEM_PROMPT = """Bạn là trợ lý pháp luật chứng khoán Việt Nam. 

Dựa trên thông tin được cung cấp, hãy trả lời câu hỏi của người dùng một cách:
- Chính xác và có căn cứ pháp lý
- Rõ ràng, dễ hiểu
- Có trích dẫn nguồn từ thông tin được cung cấp

QUAN TRỌNG: Sử dụng MARKDOWN để format, KHÔNG dùng HTML tags (không dùng <strong>, <em>, etc).
- In đậm: dùng **text**
- In nghiêng: dùng *text*
- Bullet list: dùng - hoặc •

Định dạng câu trả lời:
## 📋 Trả lời
[Nội dung trả lời chính, tổng hợp từ các nguồn]

## 📖 Căn cứ pháp lý
[Liệt kê các văn bản nguồn từ mục "Nguồn:" trong thông tin được cung cấp]
Ví dụ:
- Nghị định 155/2020/NĐ-CP
- Thông tư 96/2020/TT-BTC


"""

CHAT_SYSTEM_PROMPT = """Bạn là trợ lý pháp luật chứng khoán Việt Nam thân thiện.

Quy tắc:
1. Nếu người dùng chào (hi, hello, xin chào, chào bạn, etc.), hãy chào lại thân thiện và hỏi bạn có thể giúp gì.
2. Nếu người dùng hỏi về khả năng của bạn, hãy giới thiệu:
   - Tra cứu quy định pháp luật chứng khoán
   - Kiểm tra hiệu lực văn bản pháp luật
   - Tìm hiểu mức phạt vi phạm
   - Giải thích các điều khoản trong luật
3. KHÔNG tiếp tục nói về chủ đề cũ khi người dùng chỉ chào hoặc nói đơn giản.
4. Trả lời ngắn gọn, thân thiện, tự nhiên như đang trò chuyện.

Ví dụ:
- User: "hi" → "Xin chào bạn! 👋 Tôi có thể giúp gì về pháp luật chứng khoán hôm nay?"
- User: "hello" → "Chào bạn! Bạn cần hỗ trợ gì về chứng khoán?"
"""


class LLMClient:
    """Client for LLM interactions with API key rotation."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = None
    ):
        self.model = "gpt-4o-mini"
        # Use key manager for rotation, or single key if explicitly provided
        self._single_key = api_key
        try:
            self._key_manager = get_api_key_manager()
            logger.info(f"LLMClient initialized with {self._key_manager.get_key_count()} rotating keys")
        except Exception as e:
            logger.warning(f"Key manager init failed: {e}, using single key")
            self._key_manager = None
    
    def _get_client(self) -> AsyncOpenAI:
        """Get OpenAI client with rotated API key"""
        if self._single_key:
            api_key = self._single_key
        elif self._key_manager:
            api_key = self._key_manager.get_next_key()
        else:
            api_key = os.getenv("OPENAI_API_KEY")
        
        return AsyncOpenAI(api_key=api_key)
    
    async def generate_answer(
        self,
        query: str,
        context: str,
        trace_id: Optional[str] = None
    ) -> str:
        import time
        try:
            print(f"[LLM] Starting answer generation for query: {query[:50]}...")
            start_time = time.time()
            
            user_message = f"""Câu hỏi của người dùng: {query}
            Thông tin từ hệ thống:
            {context}
            Hãy tổng hợp và trả lời câu hỏi dựa trên thông tin trên."""

            print(f"[LLM] Calling OpenAI API with model: {self.model}")
            client = self._get_client()
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            elapsed = time.time() - start_time
            print(f"[LLM] OpenAI response received in {elapsed:.2f}s")
            
            answer = response.choices[0].message.content
            print(f"[LLM] Answer length: {len(answer)} chars")
            
            return answer
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            print(f"[LLM] ERROR: {e}")
            return ""
    
    async def generate_answer_stream(
        self,
        query: str,
        context: str,
        trace_id: Optional[str] = None
    ):
        """Generate answer with streaming - yields tokens one by one."""
        import time
        try:
            print(f"[LLM STREAM] Starting for query: {query[:50]}...")
            print(f"[LLM STREAM] Context received: {len(context)} chars")
            print(f"[LLM STREAM] Context preview:\n{context[:500]}...")
            start_time = time.time()
            
            user_message = f"""Câu hỏi của người dùng: {query}
            Thông tin từ hệ thống:
            {context}
            Hãy tổng hợp và trả lời câu hỏi dựa trên thông tin trên."""

            print(f"[LLM STREAM] Calling OpenAI with model: {self.model}")
            client = self._get_client()
            stream = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,
                max_tokens=2000,
                stream=True
            )
            
            first_token_time = None
            token_count = 0
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    if first_token_time is None:
                        first_token_time = time.time()
                        print(f"[LLM STREAM] First token at {first_token_time - start_time:.2f}s")
                    token_count += 1
                    yield chunk.choices[0].delta.content
            
            elapsed = time.time() - start_time
            print(f"[LLM STREAM] Complete: {token_count} tokens in {elapsed:.2f}s")
                
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            print(f"[LLM STREAM] ERROR: {e}")
            yield f"\n\n❌ Lỗi: {str(e)}"
    
    async def chat(self, query: str) -> str:
        """Handle general chat queries."""
        
        try:
            client = self._get_client()
            response = await client.chat.completions.create(
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
            logger.error(f"LLM chat failed: {e}")
            return ""
    
    
llm_client = LLMClient()
