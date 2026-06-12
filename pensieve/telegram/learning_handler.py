"""學習吸收 handler：偵測連結/PDF，擷取內容後經 Gemini 整理並寫入 Learn/ 筆記。"""

import asyncio
import logging
import tempfile
from pathlib import Path

from telegram import Message, Update
from telegram.ext import ContextTypes

from pensieve import gemini_client, prompts
from pensieve.learning import extractors, notes
from pensieve.telegram.handlers import is_authorized

logger = logging.getLogger(__name__)

PDF_SIZE_LIMIT_BYTES = 20 * 1024 * 1024
LEARNING_MAX_OUTPUT_TOKENS = 8192
PROCESSING_MESSAGE = "處理中，請稍候..."


def _extract_url(message: Message) -> str | None:
    for entity in message.entities or []:
        if entity.type == "url":
            return message.text[entity.offset : entity.offset + entity.length]
        if entity.type == "text_link":
            return entity.url
    return None


async def _summarize_and_save(
    status_message: Message, source_type: str, source_url: str, title: str, content: str
) -> None:
    prompt = prompts.build_learning_prompt(title, source_type, source_url, content)
    markdown = await gemini_client.generate(prompt, max_output_tokens=LEARNING_MAX_OUTPUT_TOKENS)
    relative_path = notes.write_learning_note(title, source_url, markdown)
    await status_message.edit_text(f"已寫入：{relative_path.as_posix()}")


async def handle_link_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return

    url = _extract_url(update.message)
    if url is None:
        return

    status_message = await update.message.reply_text(PROCESSING_MESSAGE)

    try:
        if extractors.is_youtube_url(url):
            title, content = await extractors.extract_youtube(url)
            source_type = "YouTube 影片"
        else:
            title, content = await extractors.extract_webpage(url)
            source_type = "網頁文章"

        await _summarize_and_save(status_message, source_type, url, title, content)
    except extractors.ExtractionError as exc:
        await status_message.edit_text(str(exc))
    except Exception:
        logger.exception("學習吸收處理失敗：%s", url)
        await status_message.edit_text("處理過程中發生錯誤，請稍後再試。")


async def handle_pdf_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_authorized(update):
        return

    document = update.message.document
    if document.file_size and document.file_size > PDF_SIZE_LIMIT_BYTES:
        await update.message.reply_text("PDF 檔案超過 20MB 上限，無法處理。")
        return

    status_message = await update.message.reply_text(PROCESSING_MESSAGE)
    fallback_title = Path(document.file_name).stem

    try:
        file = await document.get_file()
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir) / document.file_name
            await file.download_to_drive(tmp_path)
            title, content = await asyncio.to_thread(extractors.extract_pdf, tmp_path, fallback_title)

        await _summarize_and_save(status_message, "PDF 文件", document.file_name, title, content)
    except extractors.ExtractionError as exc:
        await status_message.edit_text(str(exc))
    except Exception:
        logger.exception("PDF 學習吸收處理失敗：%s", document.file_name)
        await status_message.edit_text("處理過程中發生錯誤，請稍後再試。")
