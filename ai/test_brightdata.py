"""
Test BrightData scrape capability
"""
import asyncio
from ai.mcp.brightdata import BrightDataMCPClient


async def test_scrape():
    client = BrightDataMCPClient()
    
    # First, list available tools
    print("=== Available Tools ===")
    tools = await client.list_tools()
    print(f"Tools: {tools}")
    
    # Test SERP search
    print("\n=== SERP Search ===")
    result = await client.serp_search(
        query="Quyết định 24/QĐ-HĐTV năm 2023 Điều 20 site:thuvienphapluat.vn",
        country="VN",
        language="vi",
        num_results=3
    )
    
    if result.success:
        print(f"Found {len(result.results)} results:")
        for r in result.results:
            print(f"  - {r.title}")
            print(f"    URL: {r.url}")
            print(f"    Snippet: {r.snippet[:150]}...")
    else:
        print(f"Error: {result.error}")
    
    # Test scrape if we got a result
    if result.success and result.results:
        print("\n=== Scrape First URL ===")
        url = result.results[0].url
        print(f"Scraping: {url}")
        
        scrape_result = await client.scrape_url(url)
        if scrape_result.success:
            content = scrape_result.raw_response.get("content", "")
            print(f"Scraped {len(content)} chars")
            print(f"Preview: {content[:500]}...")
        else:
            print(f"Scrape error: {scrape_result.error}")


if __name__ == "__main__":
    asyncio.run(test_scrape())
