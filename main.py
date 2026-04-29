"""
🤖 Tarjimon Bot - Main Application
Asosiy funksiya: Matn tarjima qilish + Til tanlash
"""

import asyncio
import logging
import sys

from config import dp, bot

# Database initialization
from src.db.init_db import create_all_base, init_languages_table

# Admin handlers
from src.handlers.admins.admin import admin_router
from src.handlers.admins.messages import msg_router

# User handlers
from src.handlers.users.users import user_router
from src.handlers.users.translate import translate_router
from src.handlers.users.inline_translate import inline_router

# Other handlers
from src.handlers.others.channels import channel_router
from src.handlers.others.groups import group_router
from src.handlers.others.other import other_router

# Middleware
from src.middlewares.middleware import RegisterUserMiddleware

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    logger.info("[START] Starting Tarjimon Bot...")
    try:
        await create_all_base()
        init_languages_table()
        logger.info("[OK] Database ready!")
    except Exception as e:
        logger.error(f"[ERROR] Startup error: {e}")


async def main():
    await on_startup()

    # Middleware
    dp.update.middleware(RegisterUserMiddleware())

    # Routers
    dp.include_router(admin_router)
    dp.include_router(msg_router)
    dp.include_router(user_router)
    dp.include_router(inline_router)
    dp.include_router(translate_router)   # asosiy: tarjima + til tanlash
    dp.include_router(channel_router)
    dp.include_router(group_router)
    dp.include_router(other_router)

    logger.info("[START] Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped")
    except Exception as e:
        logger.exception("Fatal error:")
        sys.exit(1)
