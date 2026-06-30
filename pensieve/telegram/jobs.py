"""每日摘要推播：擷取「今日重點與關鍵字」段落並透過 Telegram 推播。"""

import logging
from datetime import date, datetime, time, timedelta

from telegram import Bot
from telegram.ext import ContextTypes

from pensieve import config, gemini_client, prompts, state
from pensieve.context.daily_notes import (
    TAIPEI_TZ,
    build_context_bundle,
    daily_note_path,
    read_daily_note,
)
from pensieve.context.persona import load_persona

logger = logging.getLogger(__name__)

HIGHLIGHTS_HEADING = "# 今日重點與關鍵字"

TELEGRAM_MESSAGE_LIMIT = 4096

# 對應 n8n 23:30 的執行時間留出緩衝
DAILY_DIGEST_TIMES = (time(23, 45, tzinfo=TAIPEI_TZ), time(23, 55, tzinfo=TAIPEI_TZ))

MORNING_QUOTE_TIME = time(8, 0, tzinfo=TAIPEI_TZ)

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


async def _send_chunked(bot: Bot, text: str) -> None:
    """依 Telegram 訊息長度上限分段傳送。"""
    for i in range(0, len(text), TELEGRAM_MESSAGE_LIMIT):
        await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=text[i : i + TELEGRAM_MESSAGE_LIMIT])


async def _generate_daily_review() -> str:
    """以互動問答的 system prompt + context，產生口語化每日回顧。"""
    bundle = build_context_bundle()
    prompt = prompts.build_prompt(bundle, prompts.DAILY_REVIEW_PROMPT, persona=load_persona())
    return await gemini_client.generate(prompt)


async def check_and_push_digest(bot: Bot, target_date: date | None = None) -> bool:
    """檢查指定日期（預設今天）的每日彙整是否存在，存在則推播口語化回顧與重點段落、記錄已推播；回傳是否已推播。"""
    if target_date is None:
        target_date = datetime.now(TAIPEI_TZ).date()

    date_str = f"{target_date:%Y-%m-%d}"
    content = read_daily_note(target_date)
    if content is None:
        return False

    review = await _generate_daily_review()
    await _send_chunked(bot, review)

    highlights = _extract_highlights(content)
    relative_path = daily_note_path(target_date).relative_to(config.OBSIDIAN_VAULT_PATH)
    message = f"{HIGHLIGHTS_HEADING}\n\n{highlights}\n\n完整報告：{relative_path.as_posix()}"
    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=message)

    state.mark_sent(date_str)
    return True


async def run_daily(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：執行每日推播檢查。同一天若已推播過則跳過，避免 23:45/23:55 雙重排程造成重複推播。"""
    today_str = f"{datetime.now(TAIPEI_TZ).date():%Y-%m-%d}"
    if today_str in state.load_sent_dates():
        return
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
        try:
            if await check_and_push_digest(bot, target_date):
                logger.info("補推播 %s 的每日彙整", date_str)
        except Exception:
            logger.exception("補推播 %s 的每日彙整失敗，略過", date_str)


async def heartbeat_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：定期寫入心跳檔。"""
    state.write_heartbeat()


async def send_morning_quote(bot: Bot) -> None:
    """產生並推播一句心靈雞湯語錄。"""
    quote = await gemini_client.generate(prompts.MORNING_QUOTE_PROMPT)
    await bot.send_message(chat_id=config.TELEGRAM_CHAT_ID, text=quote)


async def run_morning_quote(context: ContextTypes.DEFAULT_TYPE) -> None:
    """JobQueue 排程 callback：執行心靈雞湯推播。"""
    await send_morning_quote(context.bot)
