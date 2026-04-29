# filepath: /home/adhambek/projects/pythons/tarjimon4/src/middlewares/comprehensive_middleware.py
"""
Comprehensive User Tracking Middleware
SQLite compatible version
"""
from aiogram.types import Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict

from config import db, sql, ADMIN_ID

try:
    from src.utils.gamification import GamificationEngine, DailyChallengeManager
    GAMIFICATION_ENABLED = True
except ImportError:
    GAMIFICATION_ENABLED = False
    GamificationEngine = None
    DailyChallengeManager = None


class ComprehensiveUserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        event_type = None
        if event.message:
            user = event.message.from_user
            event_type = 'message'
        elif event.callback_query:
            user = event.callback_query.from_user
            event_type = 'callback'
        if not user:
            return await handler(event, data)
        await self._process_user_activity(user, event_type)
        return await handler(event, data)

    async def _process_user_activity(self, user, event_type):
        user_id = user.id
        now = datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        today = now.strftime('%Y-%m-%d')
        try:
            sql.execute("SELECT id FROM users WHERE user_id = ?", (user_id,))
            existing = sql.fetchone()
            if not existing:
                sql.execute("""
                    INSERT OR IGNORE INTO users
                    (user_id, first_name, last_name, username, language_code,
                     is_active, created_at, updated_at, last_activity_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
                """, (user_id, user.first_name, user.last_name,
                      user.username, user.language_code,
                      now_str, now_str, now_str))
                print(f"[NEW USER] {user_id}")
            else:
                sql.execute("""
                    UPDATE users SET
                        first_name = COALESCE(?, first_name),
                        last_name   = COALESCE(?, last_name),
                        username    = COALESCE(?, username),
                        language_code = COALESCE(?, language_code),
                        last_activity_at = ?, updated_at = ?, is_active = 1
                    WHERE user_id = ?
                """, (user.first_name, user.last_name, user.username,
                      user.language_code, now_str, now_str, user_id))

            # daily activity
            sql.execute("SELECT id FROM user_activity_daily WHERE user_id=? AND activity_date=?", (user_id, today))
            if not sql.fetchone():
                sql.execute("INSERT INTO user_activity_daily (user_id, activity_date) VALUES (?,?)", (user_id, today))
            if event_type == 'message':
                sql.execute("""
                    UPDATE user_activity_daily SET session_count = session_count + 1
                    WHERE user_id=? AND activity_date=?
                """, (user_id, today))

            # session
            thirty_ago = (now - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S')
            sql.execute("""
                SELECT id FROM user_sessions
                WHERE user_id=? AND started_at>? AND ended_at IS NULL
                ORDER BY started_at DESC LIMIT 1
            """, (user_id, thirty_ago))
            if not sql.fetchone():
                sql.execute("INSERT INTO user_sessions (user_id, started_at) VALUES (?,?)", (user_id, now_str))

            if GAMIFICATION_ENABLED and GamificationEngine:
                try:
                    GamificationEngine.check_streak(user_id)
                except Exception:
                    pass

            db.commit()
        except Exception as e:
            try:
                db.rollback()
            except Exception:
                pass
            print(f"[MIDDLEWARE ERROR] {e}")


class TranslationTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        return await handler(event, data)
