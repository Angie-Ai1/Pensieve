"""每日摘要推播：擷取「今日重點與關鍵字」段落並透過 Telegram 推播。"""

from datetime import datetime, time

from telegram import Bot
from telegram.ext import ContextTypes

from pensieve import config
from pensieve.context.daily_notes import TAIPEI_TZ, daily_note_path, read_daily_note

HIGHLIGHTS_HEADING = "# 今日重點與關鍵字"

# 對應 n8n 23:30 的執行時間留出緩衝
DAILY_DIGEST_TIMES = (time(23, 45, tzinfo=TAIPEI_TZ), time(23, 55, tzinfo=TAIPEI_TZ))


def _extract_highlights(content: str) -> str:
    """從每日彙整 Markdown 擷取「今日重點與關鍵字」段落內容（至下一個 `## ` 標題前）。"""
    start = content.find(HIGHLIGHTS_HEADING)
    if start == -1:
        return content.strip()

    start += len(HIGHLIGHTS_HEADING)
    end = content.find("\n## ", start)
    section = content[start:end] if end != -1 else content[start:]
    return section.strip()


async def check_and_push_digest(bot: Bot) -> bool:
    """檢查今日彙整是否存在，存在則擷取重點段落並推播；回傳是否已推播。"""
    today = datetime.now(TAIPEI_TZ).date()
    content = read_daily_note(today)
    if content is None:
        return False

    highlights = _extract_highlights(content)
    relative_path = daily_note_path(today).relative_to(config.OBSIDIAN_VAULT_PATH)
    message = f"{HIGHLIGHTS_HEADING}\n\n{highlights}\n\n完整報告：{relative_path.as_posix()}"

    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=message)
    return True


async def run_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：執行每日推播檢查。"""
    await check_and_push_digest(context.bot)
