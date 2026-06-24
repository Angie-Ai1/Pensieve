"""互動問答 message handler，以及 /start /help 指令。"""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from pensieve import config, gemini_client, prompts
from pensieve.context.daily_notes import build_context_bundle
from pensieve.context.memory import load_memory
from pensieve.memory_update import generate_memory_draft, write_memory
from pensieve.telegram import jobs

logger = logging.getLogger(__name__)

TELEGRAM_MESSAGE_LIMIT = 4096

MEMORY_UPDATE_APPLY = "memory_update:apply"
MEMORY_UPDATE_CANCEL = "memory_update:cancel"

HELP_TEXT = (
    "我是你的個人 AI 助理，會根據 MEMORY.md 與最近的每日數位足跡彙整與你討論。\n\n"
    "直接傳訊息給我即可開始對話。\n"
    "傳 YouTube 連結、網頁連結或 PDF 檔案，我會幫你整理成學習筆記存到 Learn/。\n\n"
    "指令：\n"
    "/start - 顯示歡迎訊息\n"
    "/help - 顯示這份說明\n"
    "/digest - 顯示今日重點摘要\n"
    "/memory_update - 產生 MEMORY.md 更新草稿，確認後直接更新 MEMORY.md"
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


async def memory_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return

    status_message = await update.message.reply_text("正在產生 MEMORY.md 更新草稿...")
    draft = await generate_memory_draft()

    if draft.strip() == load_memory().strip():
        await status_message.edit_text("目前沒有需要更新的內容。")
        return

    await status_message.edit_text("已產生更新草稿，預覽如下：")
    for i in range(0, len(draft), TELEGRAM_MESSAGE_LIMIT):
        await update.message.reply_text(draft[i : i + TELEGRAM_MESSAGE_LIMIT])

    context.bot_data["memory_draft"] = draft
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("套用更新", callback_data=MEMORY_UPDATE_APPLY),
                InlineKeyboardButton("取消", callback_data=MEMORY_UPDATE_CANCEL),
            ]
        ]
    )
    await update.message.reply_text("是否套用以上更新到 MEMORY.md？", reply_markup=keyboard)


async def memory_update_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_authorized(update):
        return

    await query.answer()
    draft = context.bot_data.pop("memory_draft", None)

    if query.data == MEMORY_UPDATE_CANCEL:
        await query.edit_message_text("已取消，MEMORY.md 未變更。")
        return

    if draft is None:
        await query.edit_message_text("找不到草稿內容，請重新執行 /memory_update。")
        return

    write_memory(draft)
    await query.edit_message_text("已套用更新，MEMORY.md 已更新完成。")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        logger.warning("忽略未授權 chat_id 的訊息: %s", update.effective_chat.id)
        return

    bundle = build_context_bundle()
    prompt = prompts.build_prompt(bundle, update.message.text)
    reply = await gemini_client.generate(prompt)

    for i in range(0, len(reply), TELEGRAM_MESSAGE_LIMIT):
        await update.message.reply_text(reply[i : i + TELEGRAM_MESSAGE_LIMIT])


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """全域錯誤處理：避免任何 handler 例外時完全沒有回覆(例如 Gemini API 503)。"""
    logger.error("處理 update 時發生未預期錯誤", exc_info=context.error)
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="處理時發生錯誤，請稍後再試。",
        )
