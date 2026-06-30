"""半夜批次：把當天對話 buffer 萃取成主題記憶，成功後才清空 buffer。"""

import json
import logging
from datetime import datetime

from pensieve import gemini_client, prompts
from pensieve.context import conversation, topic_memory
from pensieve.context.daily_notes import TAIPEI_TZ

logger = logging.getLogger(__name__)


def _parse_json_array(text: str) -> list[dict]:
    """解析 Gemini 回應為 JSON 陣列，容忍外層 ```json 程式碼區塊。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[cleaned.find("\n") + 1 :] if "\n" in cleaned else cleaned[3:]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    data = json.loads(cleaned)
    if not isinstance(data, list):
        raise ValueError("萃取結果不是 JSON 陣列")
    return data


async def extract_buffer_to_topics() -> int:
    """把對話 buffer 萃取進主題記憶；成功才清空 buffer。回傳寫入的主題數。

    buffer 為空時直接回傳 0；Gemini 失敗或回應無法解析時保留 buffer 待下次重試。
    """
    buffer = conversation.load_buffer()
    if not buffer:
        logger.info("對話 buffer 為空，略過主題萃取")
        return 0

    convo = conversation.format_recent(limit=None)
    prompt = prompts.build_topic_extraction_prompt(convo, topic_memory.list_topic_names())
    raw = await gemini_client.generate(prompt)

    try:
        entries = _parse_json_array(raw)
    except (json.JSONDecodeError, ValueError):
        logger.warning("主題萃取回應無法解析為 JSON，保留 buffer 待下次重試：%s", raw[:200])
        return 0

    today = datetime.now(TAIPEI_TZ).date()
    count = 0
    for entry in entries:
        topic = (entry.get("topic") or "").strip()
        summary = (entry.get("summary") or "").strip()
        if topic and summary:
            topic_memory.append_entry(topic, summary, when=today)
            count += 1

    conversation.clear_buffer()
    logger.info("主題萃取完成：寫入 %d 個主題，已清空對話 buffer", count)
    return count
