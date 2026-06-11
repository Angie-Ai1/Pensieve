"""Gemini generateContent 輕量 wrapper（httpx）。"""

import httpx

from pensieve import config

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)


async def generate(prompt: str) -> str:
    """呼叫 Gemini generateContent，回傳第一個候選回應的文字內容。"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GEMINI_API_URL,
            params={"key": config.GEMINI_API_KEY},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["candidates"][0]["content"]["parts"][0]["text"]
