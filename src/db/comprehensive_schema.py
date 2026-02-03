"""
🔧 Comprehensive Database Schema for Tarjimon Bot Analytics
PostgreSQL version
"""
from config import db, sql


async def create_comprehensive_schema():
    """
    Create comprehensive analytics-focused database schema
    """
    print("[DB SCHEMA] Creating comprehensive analytics schema...", flush=True)
    
    try:
        # 1. CORE USERS TABLE
        sql.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                username VARCHAR(100),
                language_code VARCHAR(10) DEFAULT 'uz',
                phone_number VARCHAR(20),
                interface_lang VARCHAR(10) DEFAULT 'uz',
                default_from_lang VARCHAR(10) DEFAULT 'en',
                default_to_lang VARCHAR(10) DEFAULT 'uz',
                auto_translate BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                is_blocked BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                is_verified BOOLEAN DEFAULT FALSE,
                verified_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                source VARCHAR(50),
                referrer_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
                platform VARCHAR(50),
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] users table created", flush=True)
        
        # 2. USER SESSIONS
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                translations_count INTEGER DEFAULT 0,
                exercises_count INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                platform VARCHAR(50),
                ip_address INET,
                end_reason VARCHAR(50)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_sessions table created", flush=True)
        
        # 3. TRANSLATION HISTORY
        sql.execute("""
            CREATE TABLE IF NOT EXISTS translation_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                from_lang VARCHAR(10) NOT NULL,
                to_lang VARCHAR(10) NOT NULL,
                detected_lang VARCHAR(10),
                text_length INTEGER,
                word_count INTEGER,
                char_count INTEGER,
                method VARCHAR(50) DEFAULT 'api',
                provider VARCHAR(50),
                response_time_ms INTEGER,
                translation_mode VARCHAR(50),
                chat_type VARCHAR(50),
                chat_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id INTEGER REFERENCES user_sessions(id) ON DELETE SET NULL
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] translation_history table created", flush=True)
        
        # 4. ACHIEVEMENTS
        sql.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                emoji VARCHAR(20),
                category VARCHAR(50),
                requirement_type VARCHAR(50),
                requirement_value INTEGER DEFAULT 1,
                xp_reward INTEGER DEFAULT 0,
                badge_url TEXT,
                display_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] achievements table created", flush=True)
        
        # 5. USER ACHIEVEMENTS
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 0,
                is_unlocked BOOLEAN DEFAULT FALSE,
                context JSONB DEFAULT '{}'::jsonb,
                UNIQUE(user_id, achievement_id)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_achievements table created", flush=True)
        
        # 6. USER PREFERENCES
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                auto_detect_lang BOOLEAN DEFAULT TRUE,
                show_pronunciation BOOLEAN DEFAULT TRUE,
                show_examples BOOLEAN DEFAULT FALSE,
                default_exercise_type VARCHAR(50) DEFAULT 'flashcard',
                exercise_difficulty VARCHAR(20) DEFAULT 'adaptive',
                questions_per_session INTEGER DEFAULT 10,
                daily_reminder BOOLEAN DEFAULT TRUE,
                reminder_time TIME DEFAULT '09:00',
                streak_reminder BOOLEAN DEFAULT TRUE,
                theme VARCHAR(20) DEFAULT 'light',
                font_size VARCHAR(10) DEFAULT 'medium',
                share_progress BOOLEAN DEFAULT TRUE,
                show_on_leaderboard BOOLEAN DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_preferences table created", flush=True)
        
        # 7. DAILY CHALLENGES
        sql.execute("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id SERIAL PRIMARY KEY,
                challenge_date DATE UNIQUE NOT NULL,
                title VARCHAR(200),
                description TEXT,
                challenge_type VARCHAR(50),
                target_value INTEGER NOT NULL,
                target_unit VARCHAR(50),
                xp_reward INTEGER DEFAULT 50,
                bonus_reward TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] daily_challenges table created", flush=True)
        
        # 8. USER DAILY CHALLENGE PROGRESS
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_challenge_progress (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                challenge_id INTEGER NOT NULL REFERENCES daily_challenges(id) ON DELETE CASCADE,
                current_value INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                reward_claimed BOOLEAN DEFAULT FALSE,
                claimed_at TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_challenge_progress table created", flush=True)
        
        # 9. USER ACTIVITY DAILY
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_daily (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                activity_date DATE NOT NULL,
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
        print("[DB SCHEMA] [OK] user_activity_daily table created", flush=True)
        
        print("\n[DB SCHEMA] [SUCCESS] ALL TABLES CREATED SUCCESSFULLY!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"\n[DB SCHEMA] [ERROR]: {e}")
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
                INSERT INTO achievements (code, name, description, emoji, category, requirement_type, requirement_value, xp_reward)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING
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
