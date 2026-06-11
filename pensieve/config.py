"""讀取 .env，集中管理 pensieve 服務的設定值。"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OBSIDIAN_VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT_PATH", ""))
DAILY_NOTES_LOOKBACK_DAYS = int(os.environ.get("DAILY_NOTES_LOOKBACK_DAYS", "14"))

_REQUIRED_VARS = {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    "GEMINI_API_KEY": GEMINI_API_KEY,
    "OBSIDIAN_VAULT_PATH": str(OBSIDIAN_VAULT_PATH),
}


def validate() -> None:
    """檢查必要環境變數是否齊全，缺少時拋出例外並列出缺少的變數名稱。"""
    missing = [name for name, value in _REQUIRED_VARS.items() if not value]
    if missing:
        raise RuntimeError(f"缺少必要環境變數，請檢查 .env：{', '.join(missing)}")
