"""pensieve 自我監控狀態檔案（vault/.pensieve/）：推播紀錄、心跳檔。"""

import json
import logging
from datetime import datetime

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ

logger = logging.getLogger(__name__)

STATE_DIR = config.OBSIDIAN_VAULT_PATH / ".pensieve"
DIGEST_SENT_PATH = STATE_DIR / "digest_sent.json"
HEARTBEAT_PATH = STATE_DIR / "heartbeat.txt"

HEARTBEAT_INTERVAL_SECONDS = 3600


def load_sent_dates() -> set[str]:
    """讀取已推播日期清單（YYYY-MM-DD），檔案不存在或格式錯誤時回傳空集合。"""
    if not DIGEST_SENT_PATH.exists():
        return set()
    try:
        return set(json.loads(DIGEST_SENT_PATH.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        logger.warning("無法讀取推播狀態檔 %s，視為空", DIGEST_SENT_PATH)
        return set()


def mark_sent(date_str: str) -> None:
    """將指定日期（YYYY-MM-DD）標記為已推播，寫回狀態檔。"""
    sent = load_sent_dates()
    sent.add(date_str)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    DIGEST_SENT_PATH.write_text(
        json.dumps(sorted(sent), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def write_heartbeat() -> None:
    """寫入目前時間至心跳檔，供 n8n 心跳檢查 workflow 監控。"""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_PATH.write_text(datetime.now(TAIPEI_TZ).isoformat(), encoding="utf-8")
