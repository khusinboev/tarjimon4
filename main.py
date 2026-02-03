"""
🤖 Tarjimon Bot - Enhanced Main Application
Professional Telegram translation bot with advanced features
"""

import asyncio
import logging
import sys

from config import dp, bot, ADMIN_ID

# Database initialization
from src.db.init_db import create_all_base, init_languages_table, create_indexes_and_constraints
from src.db.enhanced_schema import DatabaseManager
from src.db.migrate_add_created_at import run_all_migrations
from src.db.comprehensive_schema import create_comprehensive_schema, init_default_achievements

# Admin handlers
from src.handlers.admins.admin import admin_router
from src.handlers.admins.messages import msg_router
from src.handlers.admins.enhanced_admin import enhanced_admin_router
from src.handlers.admins.admin_panel_complete import admin_complete_router

# User handlers
from src.handlers.users.users import user_router
from src.handlers.users.enhanced_user_panel import enhanced_user_router
from src.handlers.users.callback_handlers import callback_router
from src.handlers.users.translate import translate_router
from src.handlers.users.inline_translate import inline_router
from src.handlers.users.timetable import *

# Vocabulary handlers
from src.handlers.users.lughatlar import lughatlar_router  # Combined router for all vocabulary features

# Other handlers
from src.handlers.others.channels import channel_router
from src.handlers.others.groups import group_router
from src.handlers.others.other import other_router

# Middleware
from src.middlewares.middleware import RegisterUserMiddleware
from src.middlewares.comprehensive_middleware import ComprehensiveUserMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def on_startup() -> None:
    """Initialize all systems on startup"""
    logger.info("[START] Starting Tarjimon Bot...")
    
    try:
        # 1. Create COMPREHENSIVE analytics schema (NEW)
        logger.info("[DB] Creating comprehensive analytics schema...")
        await create_comprehensive_schema()
        
        # 2. Initialize default achievements
        logger.info("[DB] Initializing achievements...")
        await init_default_achievements()
        
        # 3. Create basic tables (legacy support)
        logger.info("[DB] Creating legacy tables...")
        await create_all_base()
        
        # 4. Run legacy migrations
        logger.info("[DB] Running legacy migrations...")
        run_all_migrations()
        
        # 5. Create enhanced tables (legacy support)
        logger.info("[DB] Creating enhanced schema (legacy)...")
        await DatabaseManager.create_enhanced_tables()
        
        # 6. Initialize languages
        logger.info("[DB] Initializing languages...")
        init_languages_table()
        
        # 7. Create indexes
        logger.info("[DB] Creating indexes...")
        create_indexes_and_constraints()
        
        # 8. Create essential and parallel vocabulary tables
        logger.info("[DB] Creating vocabulary tables...")
        try:
            from src.handlers.users.lughatlar.essential import create_essential_tables, init_essential_series
            await create_essential_tables()
            await init_essential_series()
            logger.info("[OK] Essential tables created")
        except Exception as e:
            logger.warning(f"[WARN] Essential tables: {e}")
        
        try:
            from src.handlers.users.lughatlar.parallel import create_parallel_tables, init_parallel_series
            await create_parallel_tables()
            await init_parallel_series()
            logger.info("[OK] Parallel tables created")
        except Exception as e:
            logger.warning(f"[WARN] Parallel tables: {e}")
        
        # 9. Generate daily challenge
        from src.utils.gamification import DailyChallengeManager
        DailyChallengeManager.generate_daily_challenge()
        
        logger.info("[OK] Database initialization complete!")
        logger.info("[OK] Comprehensive analytics system ready!")
        
    except Exception as e:
        logger.error(f"[ERROR] Startup error: {e}")
        raise


async def on_shutdown() -> None:
    """Cleanup on shutdown"""
    logger.info("[STOP] Shutting down bot...")
    
    try:
        await bot.session.close()
        logger.info("[OK] Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


async def main():
    """Main application entry point"""
    
    # Startup
    await on_startup()
    

    
    # Register middlewares
    dp.update.middleware(ComprehensiveUserMiddleware())  # New comprehensive tracking
    logger.info("[INIT] Comprehensive analytics middleware registered")
    
    # ==================== ROUTER REGISTRATION ====================
    
    # Admin routers (check admin privileges first)
    logger.info("[INIT] Registering admin routers...")
    dp.include_router(admin_complete_router)  # Complete working admin panel
    dp.include_router(enhanced_admin_router)  # New enhanced admin panel
    dp.include_router(admin_router)           # Original admin panel
    dp.include_router(msg_router)             # Broadcasting
    
    # # User routers
    # logger.info("[INIT] Registering user routers...")
    # dp.include_router(enhanced_user_router)   # New enhanced user panel
    # dp.include_router(callback_router)        # Callback handlers for inline keyboards
    # dp.include_router(user_router)            # Original user handlers
    # dp.include_router(inline_router)          # Inline mode
    #
    # # Vocabulary routers (combined router includes all vocabulary sub-routers)
    # logger.info("[INIT] Registering vocabulary routers...")
    # dp.include_router(lughatlar_router)       # Includes: vocabs, lughatlarim, mashqlar, ommaviylar, essential, parallel
    #
    #
    # dp.include_router(translate_router)       # Translation handlers
    #
    # # Other routers
    # logger.info("[INIT] Registering other routers...")
    # dp.include_router(channel_router)         # Channel management
    # dp.include_router(group_router)           # Group handlers
    # dp.include_router(other_router)           # Miscellaneous
    #
    # logger.info("[OK] All routers registered successfully!")
    
    # Start polling
    logger.info("[START] Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.exception("Fatal error:")
        sys.exit(1)
