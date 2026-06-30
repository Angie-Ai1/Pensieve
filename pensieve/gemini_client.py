"""Gemini generateContent 輕量 wrapper（httpx）。"""

import asyncio

import httpx

from pensieve import config

# 改用 flash-lite：免費方案每日額度遠高於 gemini-2.5-flash（後者免費僅 20 次/日），
# 且為獨立額度池，適合 pensieve 互動對話這類高頻、輕量的呼叫。
GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)

# Gemini 端在流量尖峰時段會間歇性回 503(模型暫時過載)，重試幾次通常就會打通。
RETRY_STATUS_CODES = {503}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0


async def generate(prompt: str, max_output_tokens: int | None = None) -> str:
    """呼叫 Gemini generateContent，回傳第一個候選回應的文字內容。遇到暫時性 503 會自動重試。"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if max_output_tokens is not None:
        payload["generationConfig"] = {"maxOutputTokens": max_output_tokens}

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(MAX_RETRIES + 1):
            response = await client.post(
                GEMINI_API_URL,
                params={"key": config.GEMINI_API_KEY},
                json=payload,
            )
            if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            response.raise_for_status()
            data = response.json()
            break

    return data["candidates"][0]["content"]["parts"][0]["text"]
