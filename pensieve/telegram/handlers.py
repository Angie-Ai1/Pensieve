"""互動問答 message handler，以及 /start /help 指令。"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from pensieve import config, gemini_client, prompts
from pensieve.context.daily_notes import build_context_bundle
from pensieve.telegram import jobs

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096

HELP_TEXT = (
    "我是你的個人 AI 助理，會根據 MEMORY.md 與最近的每日數位足跡彙整與你討論。\n\n"
    "直接傳訊息給我即可開始對話。\n"
    "傳 YouTube 連結、網頁連結或 PDF 檔案，我會幫你整理成學習筆記存到 Learn/。\n\n"
    "指令：\n"
    "/start - 顯示歡迎訊息\n"
    "/help - 顯示這份說明\n"
    "/digest - 顯示今日重點摘要"
)


def is_authorized(update: Update) -> bool:
    return str(update.effective_chat.id) == config.TELEGRAM_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return
    await update.message.reply_text(HELP_TEXT)


async def digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return

    sent = await jobs.check_and_push_digest(context.bot)
    if not sent:
        await update.message.reply_text("今天的彙整尚未產生，稍後再試試看。")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        logger.warning("忽略未授權 chat_id 的訊息: %s", update.effective_chat.id)
        return

    bundle = build_context_bundle()
    prompt = prompts.build_prompt(bundle, update.message.text)
    reply = await gemini_client.generate(prompt)

    for i in range(0, len(reply), TELEGRAM_MESSAGE_LIMIT):
        await update.message.reply_text(reply[i : i + TELEGRAM_MESSAGE_LIMIT])
