"""Regulatory Service - Direct MCP search and LLM answer generation.

Simplified Flow:
1. MCP BrightData search (2 best results)
2. Scrape full content from links
3. LLM generates answer directly from content
"""
import os
import logging
from typing import Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class RegulatoryService:
    """Service for finding legal documents and answering directly."""
    
    def __init__(self):
        self._brightdata = None
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm = AsyncOpenAI(api_key=self.api_key) if self.api_key else None
    
    def _get_brightdata(self):
        """Get or create BrightData MCP client."""
        if self._brightdata is None:
            from ai.mcp.brightdata import BrightDataMCPClient
            self._brightdata = BrightDataMCPClient()
        return self._brightdata
    
    async def search(self, query: str) -> dict:
        """
        Search for legal documents and generate answer directly.
        
        Flow:
        1. MCP search (2 results)
        2. Scrape content
        3. LLM generates answer
        
        Input: query string
        Output: dict with answer, found_documents, sources
        """
        try:
            brightdata = self._get_brightdata()
            
            # Step 1: Search (only 2 results)
            search_query = f"{query} site:thuvienphapluat.vn OR site:vanban.chinhphu.vn OR site:ssc.gov.vn"
            result = await brightdata.serp_search(
                query=search_query,
                country="VN",
                language="vi",
                num_results=2
            )
            
            if not (result.success and result.results):
                return {
                    "query_analysis": {"original_query": query},
                    "answer": "❌ Không tìm thấy kết quả tìm kiếm.",
                    "found_documents": [],
                    "source": "brightdata_mcp",
                    "result_summary": result.error or "Không tìm thấy kết quả"
                }
            
            # Step 2: Scrape content from top 2 URLs
            found_documents = []
            for r in result.results[:2]:
                scraped = await self._scrape_url(r.url)
                found_documents.append({
                    "title": r.title,
                    "snippet": r.snippet,
                    "url": r.url,
                    "position": r.position,
                    "full_content": scraped.get("content") if scraped.get("success") else None
                })
            
            # Step 3: Generate answer from content
            answer = await self._generate_answer(query, found_documents)
            
            return {
                "query_analysis": {"original_query": query},
                "answer": answer,
                "found_documents": found_documents,
                "source": "brightdata_mcp",
                "result_summary": f"Đã tìm thấy {len(found_documents)} văn bản liên quan."
            }
            
        except Exception as e:
            logger.error(f"Regulatory search failed: {e}", exc_info=True)
            return {
                "query_analysis": {"original_query": query},
                "answer": f"❌ Lỗi tìm kiếm: {str(e)}",
                "found_documents": [],
                "source": "error",
                "result_summary": str(e)
            }
    
    async def _scrape_url(self, url: str) -> dict:
        """Scrape content from a single URL."""
        try:
            brightdata = self._get_brightdata()
            result = await brightdata.scrape_url(url)
            
            if result.success and result.raw_response:
                content = result.raw_response.get("content", "")
                return {
                    "url": url,
                    "content": content[:8000],
                    "success": True
                }
            
            return {"url": url, "content": "", "success": False}
            
        except Exception as e:
            logger.warning(f"Scrape failed for {url}: {e}")
            return {"url": url, "content": "", "success": False}
    
    async def _generate_answer(self, query: str, documents: list) -> str:
        """Generate answer from scraped documents using LLM."""
        # Prepare context
        context_parts = []
        for i, doc in enumerate(documents):
            content = doc.get("full_content") or doc.get("snippet", "")
            if content:
                content = content.replace("\\n", "\n").replace("\\xa0", " ")
                context_parts.append(
                    f"=== Nguồn {i+1}: {doc['title']} ===\n"
                    f"URL: {doc['url']}\n\n"
                    f"{content[:4000]}\n"
                )
        
        context = "\n\n".join(context_parts)
        
        if not context:
            return "❌ Không thể đọc nội dung từ các nguồn tìm được."
        
        if not self.llm:
            sources = "\n".join([f"- [{d['title']}]({d['url']})" for d in documents])
            return f"📄 **Nội dung tìm được:**\n\n{context[:2000]}\n\n---\n📚 **Nguồn:**\n{sources}"
        
        try:
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """Bạn là chuyên gia pháp luật chứng khoán Việt Nam.

Nhiệm vụ: Trả lời câu hỏi dựa trên nội dung văn bản pháp luật được cung cấp.

Hướng dẫn:
- Trả lời chính xác dựa trên thông tin trong văn bản
- Trích dẫn số hiệu văn bản, điều khoản cụ thể
- Format câu trả lời rõ ràng với markdown"""
                    },
                    {
                        "role": "user",
                        "content": f"Câu hỏi: {query}\n\n--- NỘI DUNG VĂN BẢN ---\n{context}"
                    }
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            answer = response.choices[0].message.content
            sources = "\n".join([f"- [{d['title']}]({d['url']})" for d in documents])
            return f"{answer}\n\n---\n📚 **Nguồn tham khảo:**\n{sources}"
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            sources = "\n".join([f"- [{d['title']}]({d['url']})" for d in documents])
            return f"📄 **Nội dung tìm được:**\n\n{context[:2000]}\n\n---\n📚 **Nguồn:**\n{sources}"


# Singleton instance
_regulatory_service: Optional[RegulatoryService] = None


def get_regulatory_service() -> RegulatoryService:
    """Get or create Regulatory service instance."""
    global _regulatory_service
    if _regulatory_service is None:
        _regulatory_service = RegulatoryService()
    return _regulatory_service
