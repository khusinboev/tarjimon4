"""
🔧 Comprehensive Database Schema for Tarjimon Bot Analytics
Captures all user interactions, translations, exercises, and language usage
"""
import psycopg2
from config import db, sql, DB_CONFIG


async def create_comprehensive_schema():
    """
    Create comprehensive analytics-focused database schema
    """
    print("[DB SCHEMA] Creating comprehensive analytics schema...", flush=True)
    
    try:
        # =====================================================
        # 1. CORE USERS TABLE - Enhanced user profiles
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                
                -- Basic Profile
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                username VARCHAR(100),
                language_code VARCHAR(10) DEFAULT 'uz',
                
                -- Contact Info (if shared)
                phone_number VARCHAR(20),
                
                -- Bot Settings
                interface_lang VARCHAR(10) DEFAULT 'uz',
                default_from_lang VARCHAR(10) DEFAULT 'en',
                default_to_lang VARCHAR(10) DEFAULT 'uz',
                auto_translate BOOLEAN DEFAULT FALSE,
                
                -- User Status
                is_active BOOLEAN DEFAULT TRUE,
                is_blocked BOOLEAN DEFAULT FALSE,
                is_premium BOOLEAN DEFAULT FALSE,
                is_admin BOOLEAN DEFAULT FALSE,
                
                -- Verification
                is_verified BOOLEAN DEFAULT FALSE,
                verified_at TIMESTAMP,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Source/Referral tracking
                source VARCHAR(50),  -- 'organic', 'referral', 'ad', etc.
                referrer_id BIGINT REFERENCES users(user_id) ON DELETE SET NULL,
                
                -- Device/Client info (if available)
                platform VARCHAR(50),  -- 'ios', 'android', 'desktop', 'web'
                
                -- Metadata
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # Users indexes
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active) WHERE is_active = TRUE")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_source ON users(source)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)")
        db.commit()
        print("[DB SCHEMA] [OK] users table created", flush=True)
        
        # =====================================================
        # 2. USER SESSIONS - Track user activity sessions
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Session timing
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                
                -- Activity counts during session
                translations_count INTEGER DEFAULT 0,
                exercises_count INTEGER DEFAULT 0,
                messages_count INTEGER DEFAULT 0,
                
                -- Session metadata
                platform VARCHAR(50),
                ip_address INET,
                
                -- Session end reason
                end_reason VARCHAR(50)  -- 'timeout', 'logout', 'inactive'
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON user_sessions(started_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_time ON user_sessions(user_id, started_at)")
        db.commit()
        print("[DB SCHEMA] [OK] user_sessions table created", flush=True)
        
        # =====================================================
        # 3. TRANSLATION HISTORY - Enhanced translation tracking
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS translation_history (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Translation content
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                
                -- Language pair
                from_lang VARCHAR(10) NOT NULL,
                to_lang VARCHAR(10) NOT NULL,
                detected_lang VARCHAR(10),  -- Auto-detected source language
                
                -- Translation metadata
                text_length INTEGER,  -- Source text length
                word_count INTEGER,   -- Source word count
                char_count INTEGER,   -- Source character count
                
                -- Translation method
                method VARCHAR(50) DEFAULT 'api',  -- 'api', 'cache', 'ml', 'manual'
                provider VARCHAR(50),  -- 'google', 'libretranslate', 'my memory'
                
                -- Performance metrics
                response_time_ms INTEGER,  -- API response time
                
                -- User context
                translation_mode VARCHAR(50),  -- 'direct', 'inline', 'group'
                chat_type VARCHAR(50),  -- 'private', 'group', 'channel', 'supergroup'
                chat_id BIGINT,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Session link
                session_id INTEGER REFERENCES user_sessions(id) ON DELETE SET NULL
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_user_id ON translation_history(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_created_at ON translation_history(created_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_user_time ON translation_history(user_id, created_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_lang_pair ON translation_history(from_lang, to_lang)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_to_lang ON translation_history(to_lang)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_trans_session ON translation_history(session_id)")
        db.commit()
        print("[DB SCHEMA] [OK] translation_history table created", flush=True)
        
        # =====================================================
        # 4. LANGUAGE USAGE STATS - Aggregated language statistics
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS language_usage_stats (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Language pair
                from_lang VARCHAR(10) NOT NULL,
                to_lang VARCHAR(10) NOT NULL,
                
                -- Usage counts
                translation_count INTEGER DEFAULT 0,
                total_characters INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0,
                
                -- First and last use
                first_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Daily breakdown (optional, for trends)
                daily_stats JSONB DEFAULT '{}'::jsonb,
                
                UNIQUE(user_id, from_lang, to_lang)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_lang_stats_user ON language_usage_stats(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_lang_stats_pair ON language_usage_stats(from_lang, to_lang)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_lang_stats_last_used ON language_usage_stats(last_used_at)")
        db.commit()
        print("[DB SCHEMA] [OK] language_usage_stats table created", flush=True)
        
        # =====================================================
        # 5. VOCABULARY BOOKS (Create BEFORE practice sessions)
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS vocab_books (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Book details
                name VARCHAR(200) NOT NULL,
                description TEXT,
                emoji VARCHAR(10) DEFAULT '::books::',
                
                -- Language settings
                source_lang VARCHAR(10) DEFAULT 'en',
                target_lang VARCHAR(10) DEFAULT 'uz',
                
                -- Visibility
                is_public BOOLEAN DEFAULT FALSE,
                is_template BOOLEAN DEFAULT FALSE,
                
                -- Stats
                entry_count INTEGER DEFAULT 0,
                practice_count INTEGER DEFAULT 0,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_practiced_at TIMESTAMP,
                
                -- Metadata
                tags TEXT[],
                category VARCHAR(50),
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_vbooks_user ON vocab_books(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_vbooks_public ON vocab_books(is_public) WHERE is_public = TRUE")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_vbooks_created ON vocab_books(created_at)")
        db.commit()
        print("[DB SCHEMA] [OK] vocab_books table created", flush=True)
        
        # =====================================================
        # 6. VOCABULARY ENTRIES (Create BEFORE practice sessions)
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS vocab_entries (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL REFERENCES vocab_books(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Word/phrase data
                word_source TEXT NOT NULL,
                word_target TEXT NOT NULL,
                
                -- Additional info
                pronunciation TEXT,
                example_source TEXT,
                example_target TEXT,
                part_of_speech VARCHAR(50),  -- noun, verb, adjective, etc.
                
                -- Learning metrics
                difficulty_level INTEGER DEFAULT 1,
                mastery_level INTEGER DEFAULT 0,  -- 0-100 mastery percentage
                
                -- Practice tracking
                times_practiced INTEGER DEFAULT 0,
                times_correct INTEGER DEFAULT 0,
                times_wrong INTEGER DEFAULT 0,
                last_practiced_at TIMESTAMP,
                
                -- SRS (Spaced Repetition System)
                next_review_at TIMESTAMP,
                review_interval INTEGER DEFAULT 1,  -- Days until next review
                
                -- Status
                is_learned BOOLEAN DEFAULT FALSE,
                is_favorite BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Position in book
                position INTEGER DEFAULT 0,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ventries_book ON vocab_entries(book_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ventries_user ON vocab_entries(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ventries_learned ON vocab_entries(is_learned)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ventries_review ON vocab_entries(next_review_at)")
        db.commit()
        print("[DB SCHEMA] [OK] vocab_entries table created", flush=True)
        
        # =====================================================
        # 7. PRACTICE/EXERCISE SESSIONS - Track exercise activity
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS practice_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Session details
                session_type VARCHAR(50) NOT NULL,  -- 'flashcard', 'quiz', 'match', 'write'
                mode VARCHAR(50),  -- 'personal', 'public', 'daily_challenge'
                
                -- Vocabulary book used
                book_id INTEGER REFERENCES vocab_books(id) ON DELETE SET NULL,
                
                -- Session timing
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_seconds INTEGER,
                
                -- Performance metrics
                total_questions INTEGER DEFAULT 0,
                correct_answers INTEGER DEFAULT 0,
                wrong_answers INTEGER DEFAULT 0,
                accuracy_percentage DECIMAL(5,2) DEFAULT 0,
                
                -- Time tracking
                total_time_spent_seconds INTEGER DEFAULT 0,
                avg_response_time_seconds DECIMAL(5,2),
                
                -- Session outcome
                completed BOOLEAN DEFAULT FALSE,
                score INTEGER DEFAULT 0,
                xp_earned INTEGER DEFAULT 0,
                
                -- Difficulty settings
                difficulty VARCHAR(20),  -- 'easy', 'medium', 'hard', 'adaptive'
                
                -- Session link
                user_session_id INTEGER REFERENCES user_sessions(id) ON DELETE SET NULL,
                
                -- Metadata
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_practice_user ON practice_sessions(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_practice_type ON practice_sessions(session_type)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_practice_started ON practice_sessions(started_at)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_practice_book ON practice_sessions(book_id)")
        db.commit()
        print("[DB SCHEMA] [OK] practice_sessions table created", flush=True)
        
        # =====================================================
        # 6. PRACTICE QUESTIONS - Individual question performance
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS practice_questions (
                id SERIAL PRIMARY KEY,
                session_id INTEGER NOT NULL REFERENCES practice_sessions(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Question content
                question_type VARCHAR(50),  -- 'translate', 'multiple_choice', 'match', 'write'
                question_text TEXT,
                correct_answer TEXT,
                user_answer TEXT,
                
                -- Vocabulary reference
                vocab_entry_id INTEGER REFERENCES vocab_entries(id) ON DELETE SET NULL,
                
                -- Performance
                is_correct BOOLEAN,
                points_earned INTEGER DEFAULT 0,
                
                -- Timing
                response_time_seconds DECIMAL(5,2),
                asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                answered_at TIMESTAMP,
                
                -- Hints used
                hints_used INTEGER DEFAULT 0,
                skipped BOOLEAN DEFAULT FALSE,
                
                -- Difficulty at time of question
                difficulty_level INTEGER DEFAULT 1
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_pracq_session ON practice_questions(session_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_pracq_user ON practice_questions(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_pracq_is_correct ON practice_questions(is_correct)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_pracq_vocab ON practice_questions(vocab_entry_id)")
        db.commit()
        print("[DB SCHEMA] [OK] practice_questions table created", flush=True)
        
        # =====================================================
        # 7. EXERCISE TYPE PREFERENCES - Track favorite exercise types
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS exercise_type_stats (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                exercise_type VARCHAR(50) NOT NULL,  -- 'flashcard', 'quiz', 'match', 'write'
                
                -- Usage statistics
                session_count INTEGER DEFAULT 0,
                total_questions INTEGER DEFAULT 0,
                total_correct INTEGER DEFAULT 0,
                total_time_seconds INTEGER DEFAULT 0,
                
                -- Performance
                avg_accuracy DECIMAL(5,2),
                best_score INTEGER DEFAULT 0,
                
                -- Engagement
                last_played_at TIMESTAMP,
                streak_days INTEGER DEFAULT 0,  -- Consecutive days playing this exercise
                
                -- Preference score (calculated)
                preference_score DECIMAL(5,2) DEFAULT 0,
                
                UNIQUE(user_id, exercise_type)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_exstats_user ON exercise_type_stats(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_exstats_type ON exercise_type_stats(exercise_type)")
        db.commit()
        print("[DB SCHEMA] [OK] exercise_type_stats table created", flush=True)
        
        # =====================================================
        # 8. USER ACTIVITY DAILY - Daily aggregated activity
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_activity_daily (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                activity_date DATE NOT NULL,
                
                -- Activity counts
                translations_count INTEGER DEFAULT 0,
                translation_chars INTEGER DEFAULT 0,
                
                exercise_sessions_count INTEGER DEFAULT 0,
                exercise_questions_count INTEGER DEFAULT 0,
                exercise_correct_count INTEGER DEFAULT 0,
                
                vocab_books_created INTEGER DEFAULT 0,
                vocab_entries_added INTEGER DEFAULT 0,
                
                -- Engagement metrics
                session_count INTEGER DEFAULT 0,  -- Number of sessions
                total_time_spent_seconds INTEGER DEFAULT 0,
                
                -- Scores
                xp_earned INTEGER DEFAULT 0,
                points_earned INTEGER DEFAULT 0,
                
                -- Streak tracking
                daily_streak INTEGER DEFAULT 0,
                
                UNIQUE(user_id, activity_date)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_activity_user ON user_activity_daily(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_activity_date ON user_activity_daily(activity_date)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_date ON user_activity_daily(user_id, activity_date)")
        db.commit()
        print("[DB SCHEMA] [OK] user_activity_daily table created", flush=True)
        
        # =====================================================
        # 10. ACHIEVEMENTS
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                
                code VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                emoji VARCHAR(20),
                
                -- Category
                category VARCHAR(50),  -- 'translation', 'vocabulary', 'exercise', 'streak'
                
                -- Requirements
                requirement_type VARCHAR(50),  -- 'count', 'streak', 'score'
                requirement_value INTEGER DEFAULT 1,
                
                -- Rewards
                xp_reward INTEGER DEFAULT 0,
                badge_url TEXT,
                
                -- Display order
                display_order INTEGER DEFAULT 0,
                
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] achievements table created", flush=True)
        
        # =====================================================
        # 11. USER ACHIEVEMENTS
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                achievement_id INTEGER NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
                
                -- Unlock details
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                progress INTEGER DEFAULT 0,  -- Current progress toward achievement
                is_unlocked BOOLEAN DEFAULT FALSE,
                
                -- Context
                context JSONB DEFAULT '{}'::jsonb,  -- Details about how it was earned
                
                UNIQUE(user_id, achievement_id)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_uach_user ON user_achievements(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_uach_unlocked ON user_achievements(is_unlocked)")
        db.commit()
        print("[DB SCHEMA] [OK] user_achievements table created", flush=True)
        
        # =====================================================
        # 12. USER PREFERENCES
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Translation settings
                auto_detect_lang BOOLEAN DEFAULT TRUE,
                show_pronunciation BOOLEAN DEFAULT TRUE,
                show_examples BOOLEAN DEFAULT FALSE,
                
                -- Exercise settings
                default_exercise_type VARCHAR(50) DEFAULT 'flashcard',
                exercise_difficulty VARCHAR(20) DEFAULT 'adaptive',
                questions_per_session INTEGER DEFAULT 10,
                
                -- Notification settings
                daily_reminder BOOLEAN DEFAULT TRUE,
                reminder_time TIME DEFAULT '09:00',
                streak_reminder BOOLEAN DEFAULT TRUE,
                
                -- Display settings
                theme VARCHAR(20) DEFAULT 'light',
                font_size VARCHAR(10) DEFAULT 'medium',
                
                -- Privacy
                share_progress BOOLEAN DEFAULT TRUE,
                show_on_leaderboard BOOLEAN DEFAULT TRUE,
                
                -- Timestamps
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] user_preferences table created", flush=True)
        
        # =====================================================
        # 13. DAILY CHALLENGES
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id SERIAL PRIMARY KEY,
                
                challenge_date DATE UNIQUE NOT NULL,
                
                -- Challenge details
                title VARCHAR(200),
                description TEXT,
                challenge_type VARCHAR(50),  -- 'translation_count', 'exercise_score', 'streak'
                
                -- Target
                target_value INTEGER NOT NULL,
                target_unit VARCHAR(50),  -- 'translations', 'points', 'exercises'
                
                -- Reward
                xp_reward INTEGER DEFAULT 50,
                bonus_reward TEXT,
                
                -- Status
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        print("[DB SCHEMA] [OK] daily_challenges table created", flush=True)
        
        # =====================================================
        # 14. USER DAILY CHALLENGE PROGRESS
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_challenge_progress (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                challenge_id INTEGER NOT NULL REFERENCES daily_challenges(id) ON DELETE CASCADE,
                
                -- Progress
                current_value INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                
                -- Reward claimed
                reward_claimed BOOLEAN DEFAULT FALSE,
                claimed_at TIMESTAMP,
                
                UNIQUE(user_id, challenge_id)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ucp_user ON user_challenge_progress(user_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ucp_challenge ON user_challenge_progress(challenge_id)")
        db.commit()
        print("[DB SCHEMA] [OK] user_challenge_progress table created", flush=True)
        
        # =====================================================
        # 15. ANALYTICS AGGREGATION - Daily bot-wide stats
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS analytics_daily (
                id SERIAL PRIMARY KEY,
                stats_date DATE UNIQUE NOT NULL,
                
                -- User metrics
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,  -- Users who did any activity
                returning_users INTEGER DEFAULT 0,  -- Users who returned after 7+ days
                churned_users INTEGER DEFAULT 0,  -- Users inactive for 30+ days
                
                -- Translation metrics
                total_translations INTEGER DEFAULT 0,
                unique_translators INTEGER DEFAULT 0,
                avg_translations_per_user DECIMAL(10,2),
                
                -- Exercise metrics
                total_exercise_sessions INTEGER DEFAULT 0,
                total_questions_answered INTEGER DEFAULT 0,
                avg_accuracy DECIMAL(5,2),
                
                -- Vocabulary metrics
                new_vocab_books INTEGER DEFAULT 0,
                new_vocab_entries INTEGER DEFAULT 0,
                
                -- Engagement
                avg_session_duration_seconds INTEGER,
                total_time_spent_seconds INTEGER DEFAULT 0,
                
                -- Language popularity (top 5 stored as JSONB)
                top_language_pairs JSONB DEFAULT '{}'::jsonb,
                
                -- Calculated at
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_daily(stats_date)")
        db.commit()
        print("[DB SCHEMA] [OK] analytics_daily table created", flush=True)
        
        # =====================================================
        # 16. REFERRALS
        # =====================================================
        sql.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id SERIAL PRIMARY KEY,
                
                referrer_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                referred_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                
                -- Status
                status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'completed', 'rewarded'
                
                -- Reward
                reward_claimed BOOLEAN DEFAULT FALSE,
                reward_claimed_at TIMESTAMP,
                xp_rewarded INTEGER DEFAULT 0,
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                
                UNIQUE(referrer_id, referred_id)
            )
        """)
        
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ref_referrer ON referrals(referrer_id)")
        sql.execute("CREATE INDEX IF NOT EXISTS idx_ref_referred ON referrals(referred_id)")
        db.commit()
        print("[DB SCHEMA] [OK] referrals table created", flush=True)
        
        print("\n[DB SCHEMA] [SUCCESS] ALL TABLES CREATED SUCCESSFULLY!")
        print("[DB SCHEMA] Analytics-ready database schema is ready!")
        
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
        # Translation achievements
        ('first_translation', 'First Translation', 'Complete your first translation', '🎯', 'translation', 'count', 1, 10),
        ('translator_10', 'Translator', 'Complete 10 translations', '📝', 'translation', 'count', 10, 25),
        ('translator_100', 'Pro Translator', 'Complete 100 translations', '📚', 'translation', 'count', 100, 50),
        ('translator_1000', 'Master Translator', 'Complete 1,000 translations', '🏆', 'translation', 'count', 1000, 100),
        
        # Streak achievements
        ('streak_3', 'On Fire', '3-day streak', '🔥', 'streak', 'count', 3, 20),
        ('streak_7', 'Week Warrior', '7-day streak', '⚡', 'streak', 'count', 7, 50),
        ('streak_30', 'Monthly Master', '30-day streak', '📅', 'streak', 'count', 30, 150),
        
        # Vocabulary achievements
        ('first_vocab', 'Word Collector', 'Create your first vocabulary book', '📖', 'vocabulary', 'count', 1, 10),
        ('vocab_50', 'Word Hoarder', 'Add 50 words to vocabulary', '💎', 'vocabulary', 'count', 50, 30),
        ('vocab_master', 'Vocabulary Master', 'Add 500 words to vocabulary', '👑', 'vocabulary', 'count', 500, 100),
        
        # Exercise achievements
        ('first_exercise', 'Learner', 'Complete your first exercise session', '🧠', 'exercise', 'count', 1, 10),
        ('exercise_perfect', 'Perfect Score', 'Get 100% on an exercise', '💯', 'exercise', 'score', 100, 50),
        ('exercise_10', 'Practitioner', 'Complete 10 exercise sessions', '🎓', 'exercise', 'count', 10, 30),
        
        # Social achievements
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
