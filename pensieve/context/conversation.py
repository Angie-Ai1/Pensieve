"""即時對話 buffer：保留最近幾則 Telegram 對話，讓 pensieve 跨重啟仍能延續上下文。

存於 vault 的 .pensieve/（隨雲端硬碟同步，換機器即在）。白天累積對話，
之後（P2）由半夜批次萃取進主題記憶後清空；目前以滾動視窗保留最近 N 則訊息。
"""

import json
import logging
from datetime import datetime

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ

logger = logging.getLogger(__name__)

BUFFER_DIR = config.OBSIDIAN_VAULT_PATH / ".pensieve"
BUFFER_PATH = BUFFER_DIR / "conversation_buffer.json"

MAX_MESSAGES = 40  # 最近 N 則訊息（約 20 輪一問一答）


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


def format_recent(limit: int = MAX_MESSAGES) -> str:
    """把最近 limit 則訊息組成可讀的對話段落，供注入 prompt；buffer 為空時回傳空字串。"""
    buffer = load_buffer()[-limit:]
    lines = [
        f"{'使用者' if msg['role'] == 'user' else '你'}：{msg['text']}"
        for msg in buffer
    ]
    return "\n".join(lines)
