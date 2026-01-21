"""
Orchestrator Agent NLU - Intent classification for routing.

Classifies user queries into {type, intent} using GPT-4o-mini.
"""
import os
import json
import logging
from typing import Optional
from dataclasses import dataclass
from enum import Enum

from openai import AsyncOpenAI
from ai.utils.api_key_manager import get_api_key_manager

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """Query type for routing."""
    GENERAL_CHAT = "GENERAL_CHAT"
    NOT_RELATED = "NOT_RELATED"
    RELATED = "RELATED"


class Intent(str, Enum):
    """Intent types for legal domain."""
    LAW_CURRENCY_CHANGE = "LAW_CURRENCY_CHANGE"
    LEGAL_ANALYSIS = "LEGAL_ANALYSIS"


@dataclass
class NLUResult:
    """Result of NLU classification."""
    type: QueryType
    intent: Optional[Intent] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "intent": self.intent.value if self.intent else None
        }


CLASSIFICATION_PROMPT = """You are an NLU classifier for a Vietnamese stock law Q&A system.

Classify the user query into exactly one type and one intent (if applicable).

IMPORTANT: Questions about specific articles (Điều X), decrees (Nghị định), circulars (Thông tư), 
or any legal document content are ALWAYS "RELATED" with intent "LEGAL_ANALYSIS".

GENERAL_CHAT is VERY LIMITED to:
- Simple greetings: hello, xin chào, chào bạn
- Asking about the assistant: bạn là ai, bạn làm được gì
- Basic polite talk without legal meaning

Types:
- GENERAL_CHAT: greetings or assistant self-information ONLY
- NOT_RELATED: off-topic (weather, cooking, games, crypto prices, entertainment, etc.)
- RELATED: any question about laws, regulations, legal documents, rights, obligations, conditions, procedures, or compliance

Keywords that ALWAYS indicate RELATED:
- Điều, Khoản, Mục, Chương (article, clause, section, chapter)
- Nghị định, Thông tư, Luật, Quyết định (decree, circular, law, decision)
- quy định, hiệu lực, vi phạm, mức phạt (regulation, validity, violation, penalty)
- chứng khoán, cổ phiếu, trái phiếu, niêm yết (securities, stocks, bonds, listing)
- công bố thông tin, báo cáo, đăng ký (disclosure, report, registration)

Intents (ONLY if type = RELATED):
- LAW_CURRENCY_CHANGE: law validity, amendments, replacements, effective dates
  Keywords: còn hiệu lực, sửa đổi, thay thế, bãi bỏ, hiệu lực từ khi nào
- LEGAL_ANALYSIS: law content, conditions, procedures, rights, obligations, penalties, guidance
  Keywords: điều kiện, thủ tục, mức phạt, quy định, thanh toán, chuyển nhượng, nghĩa vụ, quyền, gồm gì, là gì, nội dung

Response format:
Return ONLY valid JSON:
{"type": "...", "intent": "..." or null}
"""



class NLUClassifier:
    """LLM-based NLU classifier using GPT-4o-mini with key rotation."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        self.model = model
        self._single_key = api_key
        # Use key manager for rotation
        try:
            self._key_manager = get_api_key_manager()
            logger.info(f"NLUClassifier: Key rotation enabled with {self._key_manager.get_key_count()} keys")
        except Exception as e:
            logger.warning(f"NLUClassifier: Key manager failed: {e}")
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
    
    async def classify(self, text: str) -> NLUResult:
        """Classify user query using GPT-4o-mini."""
        import logging
        logger = logging.getLogger(__name__)
        
        print(f"🔍 [NLU] Input: {text[:100]}")
        logger.info(f"[NLU] Input: {text[:100]}...")
        
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": CLASSIFICATION_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0,
            max_tokens=50,
            response_format={"type": "json_object"}
        )
    
        raw_result = response.choices[0].message.content
        print(f"🔍 [NLU] LLM Response: {raw_result}")
        logger.info(f"[NLU] LLM Response: {raw_result}")
        
        result = json.loads(raw_result)
        
        query_type = QueryType(result.get("type", "NOT_RELATED"))
        intent = None
        if query_type == QueryType.RELATED and result.get("intent"):
            intent = Intent(result["intent"])
        
        print(f"🔍 [NLU] Result: type={query_type.value}, intent={intent.value if intent else None}")
        logger.info(f"[NLU] Result: type={query_type.value}, intent={intent.value if intent else None}")
        
        return NLUResult(type=query_type, intent=intent)


# Singleton instance
nlu_classifier = NLUClassifier()

