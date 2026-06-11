"""pensieve 服務 entrypoint：組裝 Application、註冊 handlers、啟動 long polling。"""

import logging

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from pensieve import config
from pensieve.telegram import handlers, jobs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def main() -> None:
    config.validate()

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("digest", handlers.digest))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))

    for digest_time in jobs.DAILY_DIGEST_TIMES:
        application.job_queue.run_daily(jobs.run_daily, time=digest_time)

    application.run_polling()


if __name__ == "__main__":
    main()
