"""即時對話 buffer：保留當天 Telegram 對話，讓 pensieve 跨重啟仍能延續上下文。

存於 vault 的 .pensieve/（隨雲端硬碟同步，換機器即在）。白天累積對話，半夜由批次
萃取（memory_extract）整理進主題記憶後清空。注入即時 prompt 時只取最近一段視窗。
"""

import json
import logging
from datetime import datetime

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ

logger = logging.getLogger(__name__)

BUFFER_DIR = config.OBSIDIAN_VAULT_PATH / ".pensieve"
BUFFER_PATH = BUFFER_DIR / "conversation_buffer.json"

MAX_MESSAGES = 200  # buffer 儲存上限（一天綽綽有餘，半夜清空）
PROMPT_HISTORY_MESSAGES = 30  # 注入即時 prompt 的最近訊息數


def load_buffer() -> list[dict]:
    """讀取對話 buffer；檔案不存在或格式錯誤時回傳空 list。"""
    if not BUFFER_PATH.exists():
        return []
    try:
        return json.loads(BUFFER_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logger.warning("無法讀取對話 buffer %s，視為空", BUFFER_PATH)
        return []


def append_turn(user_text: str, assistant_text: str) -> None:
    """把一輪對話（使用者訊息 + pensieve 回覆）寫入 buffer，並裁切為最近 MAX_MESSAGES 則。"""
    now = datetime.now(TAIPEI_TZ).isoformat()
    buffer = load_buffer()
    buffer.append({"role": "user", "text": user_text, "ts": now})
    buffer.append({"role": "assistant", "text": assistant_text, "ts": now})
    buffer = buffer[-MAX_MESSAGES:]

    BUFFER_DIR.mkdir(parents=True, exist_ok=True)
    BUFFER_PATH.write_text(
        json.dumps(buffer, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def clear_buffer() -> None:
    """清空對話 buffer（半夜萃取進主題記憶後呼叫）。"""
    if BUFFER_PATH.exists():
        BUFFER_PATH.unlink()


def format_recent(limit: int | None = PROMPT_HISTORY_MESSAGES) -> str:
    """把最近 limit 則訊息組成可讀的對話段落；limit=None 取全部。buffer 為空時回傳空字串。"""
    buffer = load_buffer()
    if limit is not None:
        buffer = buffer[-limit:]
    lines = [
        f"{'使用者' if msg['role'] == 'user' else '你'}：{msg['text']}"
        for msg in buffer
    ]
    return "\n".join(lines)
