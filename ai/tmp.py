import asyncio
import os
from openai import AsyncOpenAI

async def test_openai_async():
    client = AsyncOpenAI(api_key="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")

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a test bot."},
            {"role": "user", "content": "Say hello in one sentence."}
        ],
        temperature=0,
        max_tokens=20,
    )

    print(response.choices[0].message.content)

if __name__ == "__main__":
    asyncio.run(test_openai_async())
