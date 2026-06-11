"""每日摘要推播：擷取「今日重點與關鍵字」段落並透過 Telegram 推播。"""

import logging
from datetime import date, datetime, time, timedelta

from telegram import Bot
from telegram.ext import ContextTypes

from pensieve import config, state
from pensieve.context.daily_notes import TAIPEI_TZ, daily_note_path, read_daily_note

logger = logging.getLogger(__name__)

HIGHLIGHTS_HEADING = "# 今日重點與關鍵字"

# 對應 n8n 23:30 的執行時間留出緩衝
DAILY_DIGEST_TIMES = (time(23, 45, tzinfo=TAIPEI_TZ), time(23, 55, tzinfo=TAIPEI_TZ))

# 啟動補推播時，往回檢查的天數（仿 n8n 09:00 補跑邏輯）
DIGEST_CATCHUP_DAYS = 7


def _extract_highlights(content: str) -> str:
    """從每日彙整 Markdown 擷取「今日重點與關鍵字」段落內容（至下一個 `## ` 標題前）。"""
    start = content.find(HIGHLIGHTS_HEADING)
    if start == -1:
        return content.strip()

    start += len(HIGHLIGHTS_HEADING)
    end = content.find("\n## ", start)
    section = content[start:end] if end != -1 else content[start:]
    return section.strip()


async def check_and_push_digest(bot: Bot, target_date: date | None = None) -> bool:
    """檢查指定日期（預設今天）的每日彙整是否存在，存在則擷取重點段落並推播、記錄已推播；回傳是否已推播。"""
    if target_date is None:
        target_date = datetime.now(TAIPEI_TZ).date()

    content = read_daily_note(target_date)
    if content is None:
        return False

    highlights = _extract_highlights(content)
    relative_path = daily_note_path(target_date).relative_to(config.OBSIDIAN_VAULT_PATH)
    message = f"{HIGHLIGHTS_HEADING}\n\n{highlights}\n\n完整報告：{relative_path.as_posix()}"

    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=message)
    state.mark_sent(f"{target_date:%Y-%m-%d}")
    return True


async def run_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：執行每日推播檢查。"""
    await check_and_push_digest(context.bot)


async def catch_up_digests(bot: Bot) -> None:
    """啟動時補推播：近 DIGEST_CATCHUP_DAYS 天內，daily note 已存在但尚未推播的日期。"""
    sent = state.load_sent_dates()
    today = datetime.now(TAIPEI_TZ).date()

    for offset in range(DIGEST_CATCHUP_DAYS, -1, -1):
        target_date = today - timedelta(days=offset)
        date_str = f"{target_date:%Y-%m-%d}"
        if date_str in sent:
            continue
        if await check_and_push_digest(bot, target_date):
            logger.info("補推播 %s 的每日彙整", date_str)


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：定期寫入心跳檔。"""
    state.write_heartbeat()
