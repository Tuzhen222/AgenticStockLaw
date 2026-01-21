"""Validation Service - Document validity checking."""
import os
import logging
from typing import Optional

from .a2a import get_a2a_service

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating legal document status."""
    
    def __init__(self):
        self.agent_url = os.getenv("VALIDATION_AGENT_URL", "http://localhost:9102")
        self.a2a_service = get_a2a_service()
    
    async def validate(self, query: str) -> dict:
        """
        Check validity of legal documents.
        
        Input: query about document validity
        Output: dict with document_name, is_valid, effective_date, amendments, etc.
        """
        try:
            # Call Validation Agent via A2A
            result = await self.a2a_service.call_agent(self.agent_url, query)
            
            if not result["success"]:
                return {
                    "document_name": None,
                    "is_valid": None,
                    "effective_date": None,
                    "amendments": [],
                    "replaced_by": None,
                    "raw_response": result.get("error", "Agent call failed")
                }
            
            # Parse the response - attempt to extract structured info
            content = result["parsed_content"]
            
            return {
                "document_name": self._extract_document_name(content),
                "is_valid": self._extract_validity(content),
                "effective_date": self._extract_date(content),
                "amendments": [],
                "replaced_by": None,
                "raw_response": content
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "document_name": None,
                "is_valid": None,
                "effective_date": None,
                "amendments": [],
                "replaced_by": None,
                "raw_response": f"Error: {str(e)}"
            }
    
    def _extract_document_name(self, content: str) -> Optional[str]:
        """Try to extract document name from content."""
        # Simple heuristic - look for common patterns
        import re
        patterns = [
            r"(Nghị định \d+/\d+/NĐ-CP)",
            r"(Thông tư \d+/\d+/TT-\w+)",
            r"(Luật [\w\s]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        return None
    
    def _extract_validity(self, content: str) -> Optional[bool]:
        """Try to extract validity status from content."""
        content_lower = content.lower()
        if "còn hiệu lực" in content_lower or "đang có hiệu lực" in content_lower:
            return True
        if "hết hiệu lực" in content_lower or "đã bị thay thế" in content_lower:
            return False
        return None
    
    def _extract_date(self, content: str) -> Optional[str]:
        """Try to extract effective date from content."""
        import re
        match = re.search(r"(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})", content)
        if match:
            return match.group(1)
        return None


# Singleton instance
_validation_service: Optional[ValidationService] = None


def get_validation_service() -> ValidationService:
    """Get or create Validation service instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = ValidationService()
    return _validation_service
