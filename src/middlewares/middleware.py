from aiogram.types import Update
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from config import db, sql


class RegisterUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict):
        if not event.message:
            return await handler(event, data)

        user = event.message.from_user
        user_id = user.id
        lang_code = user.language_code if user.language_code else "uz"
        username = user.username
        first_name = user.first_name

        try:
            sql.execute("SELECT user_id FROM accounts WHERE user_id = ?", (user_id,))
            if not sql.fetchone():
                sql.execute(
                    "INSERT OR IGNORE INTO accounts (user_id, lang_code, created_at, first_name, username) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?)",
                    (user_id, lang_code, first_name, username)
                )
                db.commit()

                try:
                    sql.execute("""
                        INSERT OR IGNORE INTO users_enhanced
                        (user_id, username, first_name, language_code, created_at, last_active_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (user_id, username, first_name, lang_code))
                    db.commit()

                    sql.execute("""
                        INSERT OR IGNORE INTO leaderboard (user_id, total_xp)
                        VALUES (?, 0)
                    """, (user_id,))
                    db.commit()
                except Exception as e:
                    print(f"[WARN] Could not register in enhanced tables: {e}")
                    try:
                        db.rollback()
                    except Exception:
                        pass
            else:
                try:
                    sql.execute("""
                        UPDATE accounts
                        SET first_name = COALESCE(?, first_name),
                            username = COALESCE(?, username)
                        WHERE user_id = ?
                    """, (first_name, username, user_id))

                    sql.execute("""
                        UPDATE users_enhanced
                        SET last_active_at = CURRENT_TIMESTAMP,
                            username = COALESCE(?, username),
                            first_name = COALESCE(?, first_name)
                        WHERE user_id = ?
                    """, (username, first_name, user_id))
                    db.commit()
                except Exception as e:
                    try:
                        db.rollback()
                    except Exception:
                        pass

        except Exception as e:
            print(f"[MIDDLEWARE ERROR] RegisterUser: {e}")
            try:
                db.rollback()
            except Exception:
                pass

        return await handler(event, data)
