"""NLU Service - Natural Language Understanding classification."""
import os
import json
import logging
from typing import Optional
from dataclasses import dataclass

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


CLASSIFICATION_PROMPT = """You are an NLU classifier for a Vietnamese stock law Q&A system.

Classify the user query into exactly one type and one intent (if applicable).

## Types:
- GENERAL_CHAT: Greetings, asking about capabilities, chitchat
- NOT_RELATED: Off-topic questions (gaming, cooking, unrelated domains)
- RELATED: Questions about laws, regulations, legal matters related to stock/securities

## Intents (only if type is RELATED):
- LAW_CURRENCY_CHANGE: Questions about law validity, amendments, effective dates, changes
  Examples: "còn hiệu lực không", "bị sửa đổi chưa", "thay đổi gì", "văn bản nào thay thế"
- LEGAL_ANALYSIS: Questions about law content, penalties, procedures, requirements
  Examples: "mức phạt", "quy định gì", "điều kiện", "thủ tục", "hướng dẫn"

## Response Format:
Return ONLY valid JSON:
{"type": "...", "intent": "..." or null}
"""


@dataclass
class NLUResult:
    """Result of NLU classification."""
    type: str  # GENERAL_CHAT, NOT_RELATED, RELATED
    intent: Optional[str] = None  # LAW_CURRENCY_CHANGE, LEGAL_ANALYSIS
    confidence: float = 0.0
    raw_llm_response: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "intent": self.intent,
            "confidence": self.confidence,
            "raw_llm_response": self.raw_llm_response
        }


class NLUService:
    """Service for NLU classification using LLM."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for NLU classification")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def classify(self, query: str) -> NLUResult:
        """
        Classify user query.
        
        Input: query string
        Output: NLUResult with type, intent, confidence
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_PROMPT},
                    {"role": "user", "content": query}
                ],
                temperature=0,
                max_tokens=50,
                response_format={"type": "json_object"}
            )
            
            raw_content = response.choices[0].message.content
            result = json.loads(raw_content)
            
            query_type = result.get("type", "NOT_RELATED").upper()
            intent = result.get("intent")
            if intent:
                intent = intent.upper()
            
            return NLUResult(
                type=query_type,
                intent=intent if query_type == "RELATED" else None,
                confidence=0.95,
                raw_llm_response=result
            )
            
        except Exception as e:
            logger.error(f"NLU classification failed: {e}")
            # Default to RELATED + LEGAL_ANALYSIS on error
            return NLUResult(
                type="RELATED",
                intent="LEGAL_ANALYSIS",
                confidence=0.5,
                raw_llm_response={"error": str(e)}
            )


# Singleton instance
_nlu_service: Optional[NLUService] = None


def get_nlu_service() -> NLUService:
    """Get or create NLU service instance."""
    global _nlu_service
    if _nlu_service is None:
        _nlu_service = NLUService()
    return _nlu_service
