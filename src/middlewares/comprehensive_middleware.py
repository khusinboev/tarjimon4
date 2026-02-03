"""
🔧 Comprehensive User Tracking Middleware
Captures all user interactions for analytics
"""
from aiogram.types import Update, Message, CallbackQuery
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from datetime import datetime, date, timedelta
import pytz
from typing import Any, Awaitable, Callable, Dict

from config import db, sql, ADMIN_ID

# Gamification imports
try:
    from src.utils.gamification import GamificationEngine, DailyChallengeManager
    GAMIFICATION_ENABLED = True
except ImportError:
    GAMIFICATION_ENABLED = False
    GamificationEngine = None
    DailyChallengeManager = None


class ComprehensiveUserMiddleware(BaseMiddleware):
    """
    Middleware that comprehensively tracks all user activities
    for detailed analytics and insights
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        # Extract user from event (message or callback)
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
        
        # Process user registration/activity
        await self._process_user_activity(user, event, event_type)
        
        # Continue to handler
        return await handler(event, data)
    
    async def _process_user_activity(self, user, event, event_type):
        """Process user registration and activity tracking"""
        user_id = user.id
        now = datetime.now(pytz.timezone("Asia/Tashkent"))
        today = now.date()
        
        try:
            # Check if user exists
            sql.execute("SELECT id, last_activity_at FROM users WHERE user_id = %s", (user_id,))
            existing_user = sql.fetchone()
            
            if not existing_user:
                # NEW USER - Create comprehensive profile
                await self._create_new_user(user, now)
            else:
                # EXISTING USER - Update activity
                await self._update_user_activity(user_id, user, now, existing_user[1])
            
            # Update or create daily activity record
            await self._update_daily_activity(user_id, event, event_type, now)
            
            # Manage user session
            await self._manage_session(user_id, event_type, now)
            
            # Update daily streak via gamification system
            if GAMIFICATION_ENABLED and GamificationEngine:
                try:
                    GamificationEngine.check_streak(user_id)
                except Exception as e:
                    print(f"[MIDDLEWARE] Streak check error: {e}")
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"[MIDDLEWARE ERROR] User tracking failed: {e}")
    
    async def _create_new_user(self, user, now):
        """Create comprehensive new user record"""
        user_id = user.id
        
        # Get referral info if available (from deep linking)
        # referrer_id = get_referrer_from_start_param(user_id)
        referrer_id = None
        
        sql.execute("""
            INSERT INTO users (
                user_id, first_name, last_name, username, language_code,
                interface_lang, default_from_lang, default_to_lang,
                is_active, created_at, updated_at, last_activity_at, 
                first_seen_at, referrer_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id) DO NOTHING
        """, (
            user_id,
            user.first_name,
            user.last_name,
            user.username,
            user.language_code,
            user.language_code or 'uz',  # interface_lang
            'en',  # default_from_lang
            user.language_code or 'uz',  # default_to_lang
            True,  # is_active
            now, now, now, now,
            referrer_id
        ))
        
        # Create default preferences
        sql.execute("""
            INSERT INTO user_preferences (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id,))
        
        # Initialize daily activity record
        sql.execute("""
            INSERT INTO user_activity_daily (user_id, activity_date)
            VALUES (%s, %s)
            ON CONFLICT (user_id, activity_date) DO NOTHING
        """, (user_id, now.date()))
        
        # Initialize exercise type stats
        exercise_types = ['flashcard', 'quiz', 'match', 'write']
        for ex_type in exercise_types:
            sql.execute("""
                INSERT INTO exercise_type_stats (user_id, exercise_type)
                VALUES (%s, %s)
                ON CONFLICT (user_id, exercise_type) DO NOTHING
            """, (user_id, ex_type))
        
        # Initialize user achievements
        sql.execute("""
            INSERT INTO user_achievements (user_id, achievement_id)
            SELECT %s, id FROM achievements WHERE is_active = TRUE
            ON CONFLICT DO NOTHING
        """, (user_id,))
        
        print(f"[NEW USER] Created comprehensive profile for user {user_id}")
    
    async def _update_user_activity(self, user_id, user, now, last_activity):
        """Update existing user activity"""
        # Update basic info and activity timestamp
        sql.execute("""
            UPDATE users SET
                first_name = COALESCE(%s, first_name),
                last_name = COALESCE(%s, last_name),
                username = COALESCE(%s, username),
                language_code = COALESCE(%s, language_code),
                last_activity_at = %s,
                updated_at = %s,
                is_active = TRUE
            WHERE user_id = %s
        """, (
            user.first_name, user.last_name, user.username, user.language_code,
            now, now, user_id
        ))
    
    async def _update_daily_activity(self, user_id, event, event_type, now):
        """Update daily activity statistics"""
        today = now.date()
        
        # Check if daily record exists
        sql.execute("""
            SELECT id FROM user_activity_daily 
            WHERE user_id = %s AND activity_date = %s
        """, (user_id, today))
        
        if not sql.fetchone():
            # Create new daily record
            sql.execute("""
                INSERT INTO user_activity_daily (user_id, activity_date)
                VALUES (%s, %s)
            """, (user_id, today))
        
        # Update message count
        if event_type == 'message':
            sql.execute("""
                UPDATE user_activity_daily 
                SET session_count = session_count + 1
                WHERE user_id = %s AND activity_date = %s
            """, (user_id, today))
    
    async def _manage_session(self, user_id, event_type, now):
        """Manage user session tracking"""
        # Check for active session (within last 30 minutes)
        thirty_mins_ago = now - timedelta(minutes=30)
        
        sql.execute("""
            SELECT id, started_at FROM user_sessions 
            WHERE user_id = %s AND started_at > %s AND ended_at IS NULL
            ORDER BY started_at DESC LIMIT 1
        """, (user_id, thirty_mins_ago))
        
        session = sql.fetchone()
        
        if not session:
            # Create new session
            sql.execute("""
                INSERT INTO user_sessions (user_id, started_at)
                VALUES (%s, %s)
            """, (user_id, now))


class TranslationTrackingMiddleware(BaseMiddleware):
    """
    Middleware specifically for tracking translation activity
    Should be applied to translation handlers
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        # Call handler first to get the translation result
        result = await handler(event, data)
        
        # Track translation after successful completion
        if event.message and hasattr(result, 'translation_data'):
            await self._track_translation(event.message, result.translation_data)
        
        return result
    
    async def _track_translation(self, message, trans_data):
        """Track translation in analytics"""
        user_id = message.from_user.id
        now = datetime.now(pytz.timezone("Asia/Tashkent"))
        
        try:
            # Insert translation record
            sql.execute("""
                INSERT INTO translation_history (
                    user_id, source_text, translated_text,
                    from_lang, to_lang, text_length, word_count,
                    method, chat_type, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                trans_data.get('source', ''),
                trans_data.get('translation', ''),
                trans_data.get('from_lang', 'auto'),
                trans_data.get('to_lang', 'uz'),
                len(trans_data.get('source', '')),
                len(trans_data.get('source', '').split()),
                trans_data.get('method', 'api'),
                message.chat.type,
                now
            ))
            
            # Update language usage stats
            await self._update_language_stats(
                user_id,
                trans_data.get('from_lang', 'auto'),
                trans_data.get('to_lang', 'uz'),
                len(trans_data.get('source', '')),
                len(trans_data.get('source', '').split())
            )
            
            # Update daily activity
            await self._update_daily_translation_activity(user_id, trans_data, now)
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            print(f"[TRANSLATION TRACK ERROR] {e}")
    
    async def _update_language_stats(self, user_id, from_lang, to_lang, char_count, word_count):
        """Update language usage statistics"""
        sql.execute("""
            INSERT INTO language_usage_stats (
                user_id, from_lang, to_lang, translation_count,
                total_characters, total_words, first_used_at, last_used_at
            ) VALUES (%s, %s, %s, 1, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id, from_lang, to_lang) DO UPDATE SET
                translation_count = language_usage_stats.translation_count + 1,
                total_characters = language_usage_stats.total_characters + %s,
                total_words = language_usage_stats.total_words + %s,
                last_used_at = NOW()
        """, (user_id, from_lang, to_lang, char_count, word_count, char_count, word_count))
    
    async def _update_daily_translation_activity(self, user_id, trans_data, now):
        """Update daily translation counts"""
        today = now.date()
        source_len = len(trans_data.get('source', ''))
        
        sql.execute("""
            INSERT INTO user_activity_daily (
                user_id, activity_date, translations_count, translation_chars
            ) VALUES (%s, %s, 1, %s)
            ON CONFLICT (user_id, activity_date) DO UPDATE SET
                translations_count = user_activity_daily.translations_count + 1,
                translation_chars = user_activity_daily.translation_chars + %s
        """, (user_id, today, source_len, source_len))


class ExerciseTrackingMiddleware(BaseMiddleware):
    """
    Middleware for tracking exercise/practice activity
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        
        # Track exercise start if needed
        if self._is_exercise_start(event):
            await self._track_exercise_start(event)
        
        # Call handler
        result = await handler(event, data)
        
        # Track exercise completion if applicable
        if hasattr(result, 'exercise_data'):
            await self._track_exercise_completion(event, result.exercise_data)
        
        return result
    
    def _is_exercise_start(self, event):
        """Check if this is an exercise start event"""
        if event.callback_query:
            data = event.callback_query.data or ''
            return 'exercise' in data or 'practice' in data or 'mashq' in data
        return False
    
    async def _track_exercise_start(self, event):
        """Track when user starts an exercise"""
        # Implementation based on your exercise flow
        pass
    
    async def _track_exercise_completion(self, event, exercise_data):
        """Track completed exercise"""
        # Implementation based on your exercise flow
        pass


def update_user_streak(user_id: int):
    """
    Update user daily streak
    Call this when user completes any activity
    """
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    try:
        # Check if user was active yesterday
        sql.execute("""
            SELECT 1 FROM user_activity_daily 
            WHERE user_id = %s AND activity_date = %s
        """, (user_id, yesterday))
        
        was_active_yesterday = sql.fetchone() is not None
        
        # Get current streak
        sql.execute("""
            SELECT daily_streak FROM user_activity_daily 
            WHERE user_id = %s AND activity_date = %s
        """, (user_id, today))
        
        row = sql.fetchone()
        if row:
            current_streak = row[0]
        else:
            current_streak = 0
        
        # Calculate new streak
        if was_active_yesterday:
            new_streak = current_streak + 1 if current_streak > 0 else 1
        else:
            new_streak = 1  # Start new streak
        
        # Update today's record
        sql.execute("""
            INSERT INTO user_activity_daily (user_id, activity_date, daily_streak)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, activity_date) DO UPDATE SET
                daily_streak = EXCLUDED.daily_streak
        """, (user_id, today, new_streak))
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"[STREAK UPDATE ERROR] {e}")


def check_and_unlock_achievements(user_id: int):
    """
    Check and unlock achievements for user
    Call this after significant activities
    """
    try:
        # Get user stats
        sql.execute("""
            SELECT 
                (SELECT COUNT(*) FROM translation_history WHERE user_id = %s),
                (SELECT COUNT(*) FROM practice_sessions WHERE user_id = %s),
                (SELECT COUNT(*) FROM vocab_entries WHERE user_id = %s),
                (SELECT MAX(daily_streak) FROM user_activity_daily WHERE user_id = %s)
        """, (user_id, user_id, user_id, user_id))
        
        stats = sql.fetchone()
        trans_count = stats[0] or 0
        exercise_count = stats[1] or 0
        vocab_count = stats[2] or 0
        max_streak = stats[3] or 0
        
        # Check achievements to unlock
        achievement_checks = [
            ('first_translation', trans_count >= 1),
            ('translator_10', trans_count >= 10),
            ('translator_100', trans_count >= 100),
            ('translator_1000', trans_count >= 1000),
            ('streak_3', max_streak >= 3),
            ('streak_7', max_streak >= 7),
            ('streak_30', max_streak >= 30),
            ('first_exercise', exercise_count >= 1),
            ('exercise_10', exercise_count >= 10),
            ('first_vocab', vocab_count >= 1),
            ('vocab_50', vocab_count >= 50),
        ]
        
        for achievement_code, should_unlock in achievement_checks:
            if should_unlock:
                sql.execute("""
                    UPDATE user_achievements 
                    SET is_unlocked = TRUE, unlocked_at = NOW()
                    WHERE user_id = %s AND achievement_id = (
                        SELECT id FROM achievements WHERE code = %s
                    ) AND is_unlocked = FALSE
                """, (user_id, achievement_code))
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        print(f"[ACHIEVEMENT CHECK ERROR] {e}")
