"""Test OpenAI API connection."""
import os
import asyncio
from dotenv import load_dotenv

# Load .env file
load_dotenv()

async def test_openai():
    """Test OpenAI API with current key."""
    from openai import AsyncOpenAI
    
    api_key = "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"
    print(f"API Key: {api_key[:10]}...{api_key[-5:]}" if api_key else "No API key found!")
    
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return
    
    client = AsyncOpenAI(api_key=api_key)
    
    try:
        print("\n🔄 Testing API call...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'API works!' in Vietnamese"}],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        print(f"✅ Success! Response: {result}")
        print(f"📊 Usage: {response.usage}")
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_openai())
