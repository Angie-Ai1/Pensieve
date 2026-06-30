"""Gemini generateContent 輕量 wrapper（httpx），支援多模型輪替 fallback。"""

import asyncio
import logging

import httpx

from pensieve import config

logger = logging.getLogger(__name__)

# 免費方案是「每模型每天 20 次」各自獨立計算，因此依序輪替多個模型可把免費容量
# 拉到約 N×20 次/天。順序由便宜/快到備援：flash-lite 優先，撞額度再往下退。
GEMINI_MODELS = (
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
)

GEMINI_API_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)

# 429（額度用盡）或 503（暫時過載）就改用下一個模型。
FALLBACK_STATUS_CODES = {429, 503}
# 同一個模型遇到暫時性 503 時，先就地重試幾次再換模型；429 不重試、直接換。
RETRY_STATUS_CODES = {503}
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0


async def generate(prompt: str, max_output_tokens: int | None = None) -> str:
    """呼叫 Gemini generateContent，回傳第一個候選回應的文字。

    依 GEMINI_MODELS 順序嘗試；某模型回 429/503 則改用下一個，全部失敗才拋出最後的錯誤。
    """
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if max_output_tokens is not None:
        payload["generationConfig"] = {"maxOutputTokens": max_output_tokens}

    async with httpx.AsyncClient(timeout=60.0) as client:
        last_response = None
        for model in GEMINI_MODELS:
            url = GEMINI_API_URL_TEMPLATE.format(model=model)
            for attempt in range(MAX_RETRIES + 1):
                last_response = await client.post(
                    url, params={"key": config.GEMINI_API_KEY}, json=payload
                )
                if last_response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                    continue
                break

            if last_response.status_code == 200:
                data = last_response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            if last_response.status_code in FALLBACK_STATUS_CODES:
                logger.warning(
                    "模型 %s 回傳 %s，改用下一個模型", model, last_response.status_code
                )
                continue

            # 非可輪替的錯誤（例如 400 請求格式錯誤）直接拋出，不再試其他模型。
            last_response.raise_for_status()

        # 所有模型都失敗（多半全部 429/503），拋出最後一個回應的錯誤。
        last_response.raise_for_status()
