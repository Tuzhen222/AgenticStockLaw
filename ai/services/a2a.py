"""A2A Service - Agent-to-Agent communication."""
import os
import logging
from typing import Optional, Any
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)


class A2AService:
    """Service for calling A2A agents."""
    
    def __init__(self):
        pass
    
    async def call_agent(
        self,
        agent_url: str,
        query: str,
        session_id: Optional[str] = None
    ) -> dict:
        """
        Call an A2A agent directly.
        
        Input: agent_url, query, session_id (optional)
        Output: dict with success, agent_name, raw_response, parsed_content, error
        """
        try:
            # First, get agent card
            async with httpx.AsyncClient(timeout=30.0) as client:
                card_response = await client.get(f"{agent_url}/.well-known/agent.json")
                agent_name = "Unknown"
                
                if card_response.status_code == 200:
                    card = card_response.json()
                    agent_name = card.get("name", "Unknown")
                
                # Build A2A JSON-RPC message
                message_id = str(uuid4())
                
                # Build message with session_id in metadata
                message_parts = [
                    {
                        "kind": "text",
                        "text": query
                    }
                ]
                
                # Add session_id as metadata in query if provided
                query_with_session = query
                if session_id:
                    query_with_session = f"[SESSION:{session_id}]\n{query}"
                    message_parts = [{"kind": "text", "text": query_with_session}]
                
                a2a_message = {
                    "jsonrpc": "2.0",
                    "method": "message/send",
                    "id": message_id,
                    "params": {
                        "message": {
                            "messageId": message_id,
                            "role": "user",
                            "parts": message_parts
                        }
                    }
                }
                
                # Send message to agent
                response = await client.post(
                    f"{agent_url}/",
                    json=a2a_message,
                    headers={"Content-Type": "application/json"},
                    timeout=60.0
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "agent_name": agent_name,
                        "raw_response": None,
                        "parsed_content": "",
                        "error": f"Agent returned {response.status_code}: {response.text}"
                    }
                
                result = response.json()
                
                # Debug: Print raw response
                import json as json_module
                print(f"[A2A] Raw response: {json_module.dumps(result, indent=2, default=str)[:3000]}")
                
                # Parse response content
                parsed_content = self._parse_a2a_response(result)
                print(f"[A2A] Parsed content: {len(parsed_content)} chars")
                
                return {
                    "success": True,
                    "agent_name": agent_name,
                    "raw_response": result,
                    "parsed_content": parsed_content,
                    "error": None
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "agent_name": None,
                "raw_response": None,
                "parsed_content": "",
                "error": "Request timed out"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "agent_name": None,
                "raw_response": None,
                "parsed_content": "",
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"A2A call failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent_name": None,
                "raw_response": None,
                "parsed_content": "",
                "error": str(e)
            }
    
    def _parse_a2a_response(self, result: dict) -> str:
        """Parse text content from A2A response."""
        content_parts = []
        
        if "result" in result:
            a2a_result = result["result"]
            
            # Format 0: Direct parts in result (kind=message)
            # Response format: {"result": {"kind": "message", "parts": [...], "role": "agent"}}
            if a2a_result.get("kind") == "message" and "parts" in a2a_result:
                print(f"[A2A] Found direct message format with {len(a2a_result.get('parts', []))} parts")
                for part in a2a_result.get("parts", []):
                    if isinstance(part, dict) and part.get("kind") == "text":
                        content_parts.append(part.get("text", ""))
            
            # Format 1: Nested message in result
            elif "message" in a2a_result:
                message = a2a_result["message"]
                for part in message.get("parts", []):
                    if isinstance(part, dict) and part.get("kind") == "text":
                        content_parts.append(part.get("text", ""))
            
            # Format 2: Artifacts
            if "artifacts" in a2a_result:
                for artifact in a2a_result.get("artifacts", []):
                    for part in artifact.get("parts", []):
                        if isinstance(part, dict) and part.get("kind") == "text":
                            content_parts.append(part.get("text", ""))
            
            # Format 3: Status with message
            if "status" in a2a_result:
                status = a2a_result["status"]
                if isinstance(status, dict) and "message" in status:
                    message = status["message"]
                    for part in message.get("parts", []):
                        if isinstance(part, dict) and part.get("kind") == "text":
                            content_parts.append(part.get("text", ""))
            
            # Format 4: History
            if "history" in a2a_result:
                for msg in a2a_result.get("history", []):
                    if msg.get("role") == "agent":
                        for part in msg.get("parts", []):
                            if isinstance(part, dict) and part.get("kind") == "text":
                                content_parts.append(part.get("text", ""))
        
        elif "error" in result:
            error = result["error"]
            return f"Error: {error.get('message', 'Unknown error')}"
        
        final_content = "\n".join(content_parts)
        print(f"[A2A] Parsed content: {len(final_content)} chars")
        
        return final_content


# Singleton instance
_a2a_service: Optional[A2AService] = None


def get_a2a_service() -> A2AService:
    """Get or create A2A service instance."""
    global _a2a_service
    if _a2a_service is None:
        _a2a_service = A2AService()
    return _a2a_service
