"""pensieve 服務 entrypoint：組裝 Application、註冊 handlers、啟動 long polling。"""

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from pensieve import config, state
from pensieve.telegram import handlers, jobs, learning_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def _post_init(application: Application) -> None:
    """啟動時：寫入心跳檔、補推播近期尚未送出的每日彙整。"""
    state.write_heartbeat()
    await jobs.catch_up_digests(application.bot)


def main() -> None:
    config.validate()

    application = (
        Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(_post_init).build()
    )

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("digest", handlers.digest))
    application.add_handler(CommandHandler("memory_update", handlers.memory_update))
    application.add_handler(CommandHandler("export", learning_handler.export_notes))
    application.add_handler(
        CallbackQueryHandler(
            handlers.memory_update_confirm,
            pattern=f"^{handlers.MEMORY_UPDATE_APPLY}$|^{handlers.MEMORY_UPDATE_CANCEL}$",
        )
    )
    application.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) & (filters.Entity("url") | filters.Entity("text_link")),
            learning_handler.handle_link_message,
        )
    )
    application.add_handler(MessageHandler(filters.Document.PDF, learning_handler.handle_pdf_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    application.add_error_handler(handlers.error_handler)

    for digest_time in jobs.DAILY_DIGEST_TIMES:
        application.job_queue.run_daily(jobs.run_daily, time=digest_time)

    application.job_queue.run_daily(jobs.run_morning_quote, time=jobs.MORNING_QUOTE_TIME)

    application.job_queue.run_daily(jobs.run_topic_extraction, time=jobs.TOPIC_EXTRACTION_TIME)

    application.job_queue.run_repeating(
        jobs.heartbeat_job,
        interval=state.HEARTBEAT_INTERVAL_SECONDS,
        first=state.HEARTBEAT_INTERVAL_SECONDS,
    )

    application.run_polling()


if __name__ == "__main__":
    main()
