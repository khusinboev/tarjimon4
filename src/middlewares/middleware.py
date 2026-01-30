from aiogram.types import Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware
import psycopg2
from datetime import datetime
import pytz
from config import DB_CONFIG

class RegisterUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        if not event.message:
            return await handler(event, data)  # Middleware davom etsin

        user = event.message.from_user
        user_id = user.id
        date = datetime.now(pytz.timezone("Asia/Tashkent")).date()
        lang_code = user.language_code if user.language_code else "uz"
        username = user.username
        first_name = user.first_name

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # **1️ SQL Injection xavfsizligi uchun f-string emas, parametr ishlatilmoqda**
        cur.execute("SELECT user_id FROM public.accounts WHERE user_id = %s", (user_id,))
        if not cur.fetchone():  # Foydalanuvchi bazada bo'lmasa
            cur.execute("DELETE FROM public.accounts WHERE user_id = %s", (user_id,))
            conn.commit()

            cur.execute(
                "INSERT INTO accounts (user_id, lang_code, created_at, first_name, username) VALUES (%s, %s, NOW(), %s, %s)",
                (user_id, lang_code, first_name, username)
            )
            conn.commit()
            
            # Also register in enhanced table for gamification
            try:
                cur.execute("""
                    INSERT INTO users_enhanced 
                    (user_id, username, first_name, language_code, created_at, last_active_at)
                    VALUES (%s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id, username, first_name, lang_code))
                conn.commit()
                
                # Also create leaderboard entry
                cur.execute("""
                    INSERT INTO leaderboard (user_id, total_xp, current_rank, highest_rank)
                    VALUES (%s, 0, NULL, NULL)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id,))
                conn.commit()
            except Exception as e:
                # If enhanced tables don't exist yet, just continue
                print(f"[WARN] Could not register in enhanced tables: {e}")
                conn.rollback()
        else:
            # User exists, update info in both tables
            try:
                # Update accounts table
                cur.execute("""
                    UPDATE accounts 
                    SET first_name = COALESCE(%s, first_name),
                        username = COALESCE(%s, username),
                        updated_at = NOW()
                    WHERE user_id = %s
                """, (first_name, username, user_id))
                
                # Update enhanced table
                cur.execute("""
                    UPDATE users_enhanced 
                    SET last_active_at = NOW(),
                        username = COALESCE(%s, username),
                        first_name = COALESCE(%s, first_name)
                    WHERE user_id = %s
                """, (username, first_name, user_id))
                conn.commit()
            except Exception as e:
                conn.rollback()

        cur.close()
        conn.close()

        return await handler(event, data)  # **2 Xatolik tuzatildi, middleware davom etadi**
