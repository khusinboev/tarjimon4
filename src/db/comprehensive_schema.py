"""
🔧 Comprehensive Database Schema for Tarjimon Bot Analytics
SQLite compatible version
"""
from config import db, sql


async def create_comprehensive_schema():
    """Create comprehensive analytics-focused database schema"""
    print("[DB SCHEMA] Creating comprehensive analytics schema...", flush=True)

    try:
        sql.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                first_name TEXT, last_name TEXT, username TEXT,
                language_code TEXT DEFAULT 'uz',
                phone_number TEXT,
                interface_lang TEXT DEFAULT 'uz',
                default_from_lang TEXT DEFAULT 'en',
                default_to_lang TEXT DEFAULT 'uz',
                auto_translate INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                is_blocked INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_verified INTEGER DEFAULT 0,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source TEXT, referrer_id INTEGER, platform TEXT
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] users table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                translations_count INTEGER DEFAULT 0,
                exercises_count INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                platform TEXT, end_reason TEXT
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_sessions table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS translation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                from_lang TEXT NOT NULL,
                to_lang TEXT NOT NULL,
                detected_lang TEXT,
                text_length INTEGER, word_count INTEGER, char_count INTEGER,
                method TEXT DEFAULT 'api', provider TEXT, response_time_ms INTEGER,
                translation_mode TEXT, chat_type TEXT, chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id INTEGER
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] translation_history table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT, emoji TEXT, category TEXT,
                requirement_type TEXT,
                requirement_value INTEGER DEFAULT 1,
                xp_reward INTEGER DEFAULT 0,
                badge_url TEXT, display_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] achievements table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 0,
                is_unlocked INTEGER DEFAULT 0,
                UNIQUE(user_id, achievement_id)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_achievements table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                auto_detect_lang INTEGER DEFAULT 1,
                show_pronunciation INTEGER DEFAULT 1,
                show_examples INTEGER DEFAULT 0,
                default_exercise_type TEXT DEFAULT 'flashcard',
                exercise_difficulty TEXT DEFAULT 'adaptive',
                questions_per_session INTEGER DEFAULT 10,
                daily_reminder INTEGER DEFAULT 1,
                reminder_time TEXT DEFAULT '09:00',
                streak_reminder INTEGER DEFAULT 1,
                theme TEXT DEFAULT 'light',
                font_size TEXT DEFAULT 'medium',
                share_progress INTEGER DEFAULT 1,
                show_on_leaderboard INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_preferences table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                challenge_date TEXT UNIQUE NOT NULL,
                title TEXT, description TEXT, challenge_type TEXT,
                target_value INTEGER NOT NULL,
                target_unit TEXT,
                xp_reward INTEGER DEFAULT 50,
                bonus_reward TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] daily_challenges table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_challenge_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, challenge_id INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                is_completed INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                reward_claimed INTEGER DEFAULT 0,
                claimed_at TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_challenge_progress table created", flush=True)

        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_daily (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL, activity_date TEXT NOT NULL,
                translations_count INTEGER DEFAULT 0,
                translation_chars INTEGER DEFAULT 0,
                exercise_sessions_count INTEGER DEFAULT 0,
                exercise_questions_count INTEGER DEFAULT 0,
                exercise_correct_count INTEGER DEFAULT 0,
                vocab_books_created INTEGER DEFAULT 0,
                vocab_entries_added INTEGER DEFAULT 0,
                session_count INTEGER DEFAULT 0,
                total_time_spent_seconds INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                points_earned INTEGER DEFAULT 0,
                daily_streak INTEGER DEFAULT 0,
                UNIQUE(user_id, activity_date)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [SUCCESS] ALL TABLES CREATED SUCCESSFULLY!")
        return True

    except Exception as e:
        db.rollback()
        print(f"[DB SCHEMA] [ERROR]: {e}")
        import traceback
        traceback.print_exc()
        return False


async def init_default_achievements():
    """Initialize default achievements"""
    print("[DB SCHEMA] Initializing default achievements...", flush=True)

    achievements = [
        ('first_translation', 'First Translation', 'Complete your first translation', '🎯', 'translation', 'count', 1, 10),
        ('translator_10', 'Translator', 'Complete 10 translations', '📝', 'translation', 'count', 10, 25),
        ('translator_100', 'Pro Translator', 'Complete 100 translations', '📚', 'translation', 'count', 100, 50),
        ('translator_1000', 'Master Translator', 'Complete 1,000 translations', '🏆', 'translation', 'count', 1000, 100),
        ('streak_3', 'On Fire', '3-day streak', '🔥', 'streak', 'count', 3, 20),
        ('streak_7', 'Week Warrior', '7-day streak', '⚡', 'streak', 'count', 7, 50),
        ('streak_30', 'Monthly Master', '30-day streak', '📅', 'streak', 'count', 30, 150),
        ('first_vocab', 'Word Collector', 'Create your first vocabulary book', '📖', 'vocabulary', 'count', 1, 10),
        ('vocab_50', 'Word Hoarder', 'Add 50 words to vocabulary', '💎', 'vocabulary', 'count', 50, 30),
        ('vocab_master', 'Vocabulary Master', 'Add 500 words to vocabulary', '👑', 'vocabulary', 'count', 500, 100),
        ('first_exercise', 'Learner', 'Complete your first exercise session', '🧠', 'exercise', 'count', 1, 10),
        ('exercise_perfect', 'Perfect Score', 'Get 100% on an exercise', '💯', 'exercise', 'score', 100, 50),
        ('exercise_10', 'Practitioner', 'Complete 10 exercise sessions', '🎓', 'exercise', 'count', 10, 30),
        ('referral_1', 'Influencer', 'Refer 1 friend', '👥', 'social', 'count', 1, 25),
        ('referral_5', 'Ambassador', 'Refer 5 friends', '🌟', 'social', 'count', 5, 100),
    ]

    try:
        for code, name, description, emoji, category, req_type, req_val, xp in achievements:
            sql.execute("""
                INSERT OR IGNORE INTO achievements
                (code, name, description, emoji, category, requirement_type, requirement_value, xp_reward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (code, name, description, emoji, category, req_type, req_val, xp))
        db.commit()
        print(f"[DB SCHEMA] [OK] {len(achievements)} default achievements initialized")
        return True
    except Exception as e:
        db.rollback()
        print(f"[DB SCHEMA] [WARN] Error initializing achievements: {e}")
        return False


if __name__ == "__main__":
    import asyncio
    asyncio.run(create_comprehensive_schema())
    asyncio.run(init_default_achievements())
