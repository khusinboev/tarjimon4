"""
🗄️ Enhanced Database Schema for Tarjimon Bot
Advanced multi-faceted database structure with comprehensive features
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from config import db, sql, LANGUAGES


class DatabaseManager:
    """🏗️ Advanced Database Management System"""
    
    @staticmethod
    async def create_enhanced_tables():
        """Create all enhanced tables with sophisticated structure"""
        
        # ==========================================
        # 1️⃣ USERS & AUTHENTICATION
        # ==========================================
        
        # Enhanced users table with premium features
        sql.execute("""
            CREATE TABLE IF NOT EXISTS users_enhanced (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL UNIQUE,
                username VARCHAR(100),
                first_name VARCHAR(200),
                last_name VARCHAR(200),
                language_code VARCHAR(10) DEFAULT 'uz',
                interface_language VARCHAR(10) DEFAULT 'uz',
                is_premium BOOLEAN DEFAULT FALSE,
                premium_until TIMESTAMP,
                daily_quota INTEGER DEFAULT 100,
                used_quota_today INTEGER DEFAULT 0,
                quota_reset_date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                last_active_at TIMESTAMP DEFAULT NOW(),
                is_blocked BOOLEAN DEFAULT FALSE,
                block_reason TEXT,
                reputation_score INTEGER DEFAULT 100,
                experience_points INTEGER DEFAULT 0,
                user_level INTEGER DEFAULT 1,
                streak_days INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_streak_date DATE,
                theme_preference VARCHAR(20) DEFAULT 'default',
                notifications_enabled BOOLEAN DEFAULT TRUE,
                sound_enabled BOOLEAN DEFAULT TRUE,
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # User sessions for tracking activity
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                session_start TIMESTAMP DEFAULT NOW(),
                session_end TIMESTAMP,
                duration_minutes INTEGER,
                actions_count INTEGER DEFAULT 0,
                device_info TEXT,
                ip_address INET,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE
            )
        """)
        
        # ==========================================
        # 2️⃣ TRANSLATION SYSTEM
        # ==========================================
        
        # Enhanced translation history with AI features
        sql.execute("""
            CREATE TABLE IF NOT EXISTS translations_enhanced (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                from_lang VARCHAR(10) NOT NULL,
                to_lang VARCHAR(10) NOT NULL,
                original_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                detected_lang VARCHAR(10),
                confidence_score DECIMAL(5,4),
                text_length INTEGER,
                translation_time_ms INTEGER,
                engine_used VARCHAR(50) DEFAULT 'google',
                is_favorite BOOLEAN DEFAULT FALSE,
                favorite_note TEXT,
                tags TEXT[],
                category VARCHAR(50),
                usage_count INTEGER DEFAULT 1,
                last_used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                context JSONB DEFAULT '{}'::jsonb,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE
            )
        """)
        
        # Translation cache for performance
        sql.execute("""
            CREATE TABLE IF NOT EXISTS translation_cache (
                id SERIAL PRIMARY KEY,
                from_lang VARCHAR(10) NOT NULL,
                to_lang VARCHAR(10) NOT NULL,
                original_hash VARCHAR(64) UNIQUE,
                original_text TEXT,
                translated_text TEXT NOT NULL,
                hit_count INTEGER DEFAULT 1,
                last_accessed TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '30 days'
            )
        """)
        
        # Pronunciation guide
        sql.execute("""
            CREATE TABLE IF NOT EXISTS pronunciation_guides (
                id SERIAL PRIMARY KEY,
                word TEXT NOT NULL,
                lang_code VARCHAR(10) NOT NULL,
                phonetic TEXT,
                audio_url TEXT,
                syllables TEXT[],
                stress_position INTEGER,
                examples TEXT[],
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(word, lang_code)
            )
        """)
        
        # ==========================================
        # 3️⃣ VOCABULARY & LEARNING SYSTEM
        # ==========================================
        
        # Enhanced vocabulary books with rich metadata
        sql.execute("""
            CREATE TABLE IF NOT EXISTS vocab_books_enhanced (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                cover_image_url TEXT,
                color_theme VARCHAR(20) DEFAULT 'blue',
                icon_emoji VARCHAR(10) DEFAULT '📚',
                src_lang VARCHAR(10) DEFAULT 'en',
                trg_lang VARCHAR(10) DEFAULT 'uz',
                is_public BOOLEAN DEFAULT FALSE,
                is_official BOOLEAN DEFAULT FALSE,
                difficulty_level VARCHAR(20) DEFAULT 'beginner',
                category VARCHAR(50) DEFAULT 'general',
                tags TEXT[],
                total_words INTEGER DEFAULT 0,
                learned_words INTEGER DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                average_rating DECIMAL(3,2),
                download_count INTEGER DEFAULT 0,
                forked_from INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                last_studied_at TIMESTAMP,
                meta JSONB DEFAULT '{}'::jsonb,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE SET NULL,
                FOREIGN KEY (forked_from) REFERENCES vocab_books_enhanced(id) ON DELETE SET NULL
            )
        """)
        
        # Enhanced vocabulary entries
        sql.execute("""
            CREATE TABLE IF NOT EXISTS vocab_entries_enhanced (
                id SERIAL PRIMARY KEY,
                book_id INTEGER NOT NULL,
                word_src TEXT NOT NULL,
                word_trg TEXT NOT NULL,
                pronunciation TEXT,
                part_of_speech VARCHAR(50),
                definition_src TEXT,
                definition_trg TEXT,
                example_src TEXT,
                example_trg TEXT,
                synonyms TEXT[],
                antonyms TEXT[],
                images TEXT[],
                audio_src_url TEXT,
                audio_trg_url TEXT,
                difficulty VARCHAR(20) DEFAULT 'medium',
                frequency_rank INTEGER,
                notes TEXT,
                position INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (book_id) REFERENCES vocab_books_enhanced(id) ON DELETE CASCADE
            )
        """)
        
        # Spaced repetition system
        sql.execute("""
            CREATE TABLE IF NOT EXISTS srs_cards (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                entry_id INTEGER NOT NULL,
                ease_factor DECIMAL(4,2) DEFAULT 2.5,
                interval_days INTEGER DEFAULT 0,
                repetitions INTEGER DEFAULT 0,
                lapses INTEGER DEFAULT 0,
                due_date DATE DEFAULT CURRENT_DATE,
                last_reviewed TIMESTAMP,
                next_review TIMESTAMP,
                review_history JSONB DEFAULT '[]'::jsonb,
                status VARCHAR(20) DEFAULT 'learning',
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (entry_id) REFERENCES vocab_entries_enhanced(id) ON DELETE CASCADE,
                UNIQUE(user_id, entry_id)
            )
        """)
        
        # Learning goals
        sql.execute("""
            CREATE TABLE IF NOT EXISTS learning_goals (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                goal_type VARCHAR(50) NOT NULL,
                target_value INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                target_lang VARCHAR(10),
                book_ids INTEGER[],
                start_date DATE DEFAULT CURRENT_DATE,
                deadline DATE,
                reminder_time TIME,
                is_active BOOLEAN DEFAULT TRUE,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                streak_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE
            )
        """)
        
        # Study sessions tracking
        sql.execute("""
            CREATE TABLE IF NOT EXISTS study_sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                book_id INTEGER,
                session_type VARCHAR(50) DEFAULT 'review',
                started_at TIMESTAMP DEFAULT NOW(),
                ended_at TIMESTAMP,
                duration_seconds INTEGER,
                cards_studied INTEGER DEFAULT 0,
                correct_count INTEGER DEFAULT 0,
                wrong_count INTEGER DEFAULT 0,
                accuracy_rate DECIMAL(5,2),
                xp_earned INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES vocab_books_enhanced(id) ON DELETE SET NULL
            )
        """)
        
        # ==========================================
        # 4️⃣ ACHIEVEMENTS & GAMIFICATION
        # ==========================================
        
        # Achievements catalog
        sql.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id SERIAL PRIMARY KEY,
                code VARCHAR(100) UNIQUE NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                icon_emoji VARCHAR(10) DEFAULT '🏆',
                rarity VARCHAR(20) DEFAULT 'common',
                category VARCHAR(50),
                requirement_type VARCHAR(50),
                requirement_value INTEGER,
                xp_reward INTEGER DEFAULT 0,
                is_hidden BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # User achievements
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT NOW(),
                progress INTEGER DEFAULT 0,
                is_claimed BOOLEAN DEFAULT FALSE,
                claimed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
                UNIQUE(user_id, achievement_id)
            )
        """)
        
        # Daily challenges
        sql.execute("""
            CREATE TABLE IF NOT EXISTS daily_challenges (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE DEFAULT CURRENT_DATE,
                title VARCHAR(200),
                description TEXT,
                challenge_type VARCHAR(50),
                target_value INTEGER,
                reward_xp INTEGER,
                reward_premium_days INTEGER DEFAULT 0
            )
        """)
        
        # User daily challenge progress
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_challenges (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                challenge_id INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (challenge_id) REFERENCES daily_challenges(id) ON DELETE CASCADE,
                UNIQUE(user_id, challenge_id)
            )
        """)
        
        # Leaderboard
        sql.execute("""
            CREATE TABLE IF NOT EXISTS leaderboard (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                total_xp INTEGER DEFAULT 0,
                monthly_xp INTEGER DEFAULT 0,
                weekly_xp INTEGER DEFAULT 0,
                current_rank INTEGER,
                highest_rank INTEGER,
                translations_count INTEGER DEFAULT 0,
                words_learned INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE
            )
        """)
        
        # ==========================================
        # 5️⃣ ADMIN & ANALYTICS
        # ==========================================
        
        # Admin action logs
        sql.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id SERIAL PRIMARY KEY,
                admin_id BIGINT NOT NULL,
                action_type VARCHAR(100) NOT NULL,
                target_type VARCHAR(50),
                target_id BIGINT,
                details JSONB,
                ip_address INET,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # System analytics
        sql.execute("""
            CREATE TABLE IF NOT EXISTS system_analytics (
                id SERIAL PRIMARY KEY,
                date DATE UNIQUE DEFAULT CURRENT_DATE,
                new_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_translations INTEGER DEFAULT 0,
                total_words_added INTEGER DEFAULT 0,
                premium_users INTEGER DEFAULT 0,
                revenue DECIMAL(10,2) DEFAULT 0,
                avg_session_duration INTEGER,
                peak_hour INTEGER,
                top_languages JSONB,
                error_count INTEGER DEFAULT 0,
                api_response_time_ms INTEGER
            )
        """)
        
        # User feedback
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_feedback (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                feedback_type VARCHAR(50) NOT NULL,
                rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                message TEXT,
                screenshot_url TEXT,
                is_resolved BOOLEAN DEFAULT FALSE,
                resolved_by BIGINT,
                resolved_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE
            )
        """)
        
        # ==========================================
        # 6️⃣ SOCIAL FEATURES
        # ==========================================
        
        # User follows
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_follows (
                id SERIAL PRIMARY KEY,
                follower_id BIGINT NOT NULL,
                following_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (follower_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (following_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                UNIQUE(follower_id, following_id)
            )
        """)
        
        # Shared vocab collections
        sql.execute("""
            CREATE TABLE IF NOT EXISTS shared_collections (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                book_id INTEGER NOT NULL,
                share_code VARCHAR(20) UNIQUE,
                share_message TEXT,
                access_count INTEGER DEFAULT 0,
                likes_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                FOREIGN KEY (book_id) REFERENCES vocab_books_enhanced(id) ON DELETE CASCADE
            )
        """)
        
        # Collection likes
        sql.execute("""
            CREATE TABLE IF NOT EXISTS collection_likes (
                id SERIAL PRIMARY KEY,
                collection_id INTEGER NOT NULL,
                user_id BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                FOREIGN KEY (collection_id) REFERENCES shared_collections(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users_enhanced(user_id) ON DELETE CASCADE,
                UNIQUE(collection_id, user_id)
            )
        """)
        
        # ==========================================
        # CREATE INDEXES
        # ==========================================
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_enhanced_user_id ON users_enhanced(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_users_enhanced_premium ON users_enhanced(is_premium) WHERE is_premium = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_translations_user ON translations_enhanced(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_translations_favorite ON translations_enhanced(user_id, is_favorite) WHERE is_favorite = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_cache_hash ON translation_cache(original_hash)",
            "CREATE INDEX IF NOT EXISTS idx_vocab_books_user ON vocab_books_enhanced(user_id, is_public)",
            "CREATE INDEX IF NOT EXISTS idx_vocab_entries_book ON vocab_entries_enhanced(book_id, is_active)",
            "CREATE INDEX IF NOT EXISTS idx_srs_due ON srs_cards(user_id, due_date)",
            "CREATE INDEX IF NOT EXISTS idx_srs_cards_user ON srs_cards(user_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_study_sessions_user ON study_sessions(user_id, started_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_achievements_user ON user_achievements(user_id, unlocked_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_leaderboard_xp ON leaderboard(total_xp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_admin_logs ON admin_logs(admin_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_date ON system_analytics(date DESC)",
        ]
        
        for idx_sql in indexes:
            try:
                sql.execute(idx_sql)
            except Exception as e:
                print(f"[WARN] Index creation warning: {e}")
        
        db.commit()
        print("[OK] Enhanced database schema created successfully!")
        return True
    
    @staticmethod
    async def init_default_achievements():
        """Initialize default achievements"""
        achievements = [
            ('first_translation', "🌟 Birinchi Tarjima", "Birinchi tarjimangizni bajardingiz", '🌟', 'common', 'milestone', 'translations_count', 1, 10),
            ('translation_novice', "📝 Tarjima Novatori", "100 ta tarjima bajardingiz", '📝', 'common', 'milestone', 'translations_count', 100, 50),
            ('translation_expert', "🎯 Tarjima Eksperti", "1000 ta tarjima bajardingiz", '🎯', 'rare', 'milestone', 'translations_count', 1000, 200),
            ('translation_master', "👑 Tarjima Ustasi", "10000 ta tarjima bajardingiz", '👑', 'legendary', 'milestone', 'translations_count', 10000, 1000),
            ('vocab_collector', "📚 Lug'at Jamlovchi", "Birinchi lug'atingizni yaratdingiz", '📚', 'common', 'milestone', 'vocab_books_count', 1, 20),
            ('word_hoarder', "💎 So'z Xazinachisi", "1000 ta so'z qo'shdingiz", '💎', 'rare', 'milestone', 'words_count', 1000, 100),
            ('streak_week', "🔥 Bir Haftalik Izchillik", "7 kun ketma-ket o'qidingiz", '🔥', 'common', 'streak', 'streak_days', 7, 50),
            ('streak_month', "⚡ Bir Oylik Izchillik", "30 kun ketma-ket o'qidingiz", '⚡', 'rare', 'streak', 'streak_days', 30, 200),
            ('streak_century', "🌟 Yuz Kunlik Izchillik", "100 kun ketma-ket o'qidingiz", '🌟', 'legendary', 'streak', 'streak_days', 100, 1000),
            ('polyglot_beginner', "🌍 Til O'rganuvchi", "3 ta turli tilga tarjima qildingiz", '🌍', 'common', 'languages', 'unique_languages', 3, 30),
            ('polyglot_master', "🌐 Poliglot", "10 ta turli tilga tarjima qildingiz", '🌐', 'legendary', 'languages', 'unique_languages', 10, 500),
            ('social_butterfly', "🦋 Ijtimoiy Kapalak", "Birinchi ommaviy lug'atingizni yaratdingiz", '🦋', 'common', 'social', 'public_books', 1, 25),
            ('influencer', "⭐ Influencer", "Lug'atingiz 100 marta yuklandi", '⭐', 'rare', 'social', 'book_downloads', 100, 150),
            ('perfect_score', "💯 Mukammal Natija", "Mashqda 100% natija ko'rsatdingiz", '💯', 'rare', 'practice', 'perfect_practice', 1, 100),
            ('early_bird', "🐥 Erta Qush", "Ertalabki soat 6 da o'qishni boshladingiz", '🐥', 'common', 'habit', 'early_morning', 1, 20),
            ('night_owl', "🦉 Tunlik Boyqush", "Tungi soat 12 dan keyin o'qidingiz", '🦉', 'common', 'habit', 'night_study', 1, 20),
            ('explorer', "🔍 Tadqiqotchi", "Barcha bo'limlarni ochdingiz", '🔍', 'rare', 'exploration', 'all_sections', 1, 100),
        ]
        
        for ach in achievements:
            try:
                sql.execute("""
                    INSERT INTO achievements 
                    (code, name, description, icon_emoji, rarity, category, requirement_type, requirement_value, xp_reward)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (code) DO NOTHING
                """, ach)
            except Exception as e:
                print(f"[WARN] Achievement insert warning: {e}")
        
        db.commit()
        print(f"[OK] {len(achievements)} achievements initialized!")
    
    @staticmethod
    async def migrate_existing_data():
        """Migrate data from old tables to new enhanced tables"""
        try:
            # Migrate users
            sql.execute("""
                INSERT INTO users_enhanced (user_id, username, first_name, language_code, created_at)
                SELECT user_id, username, first_name, lang_code, COALESCE(created_at, NOW())
                FROM accounts
                ON CONFLICT (user_id) DO NOTHING
            """)
            
            # Migrate translations
            sql.execute("""
                INSERT INTO translations_enhanced 
                (user_id, from_lang, to_lang, original_text, translated_text, created_at)
                SELECT user_id, from_lang, to_lang, original_text, translated_text, created_at
                FROM translation_history
                ON CONFLICT DO NOTHING
            """)
            
            db.commit()
            print("[OK] Data migration completed!")
            return True
        except Exception as e:
            print(f"[WARN] Migration warning: {e}")
            return False


# Helper functions for common operations
async def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Get comprehensive user statistics"""
    try:
        sql.execute("""
            SELECT 
                ue.total_xp,
                ue.user_level,
                ue.streak_days,
                ue.longest_streak,
                ue.experience_points,
                COUNT(DISTINCT te.id) as total_translations,
                COUNT(DISTINCT vb.id) as vocab_books_count,
                COUNT(DISTINCT ve.id) as total_words
            FROM users_enhanced ue
            LEFT JOIN translations_enhanced te ON ue.user_id = te.user_id
            LEFT JOIN vocab_books_enhanced vb ON ue.user_id = vb.user_id
            LEFT JOIN vocab_entries_enhanced ve ON vb.id = ve.book_id
            WHERE ue.user_id = %s
            GROUP BY ue.user_id
        """, (user_id,))
        
        result = sql.fetchone()
        if result:
            return {
                'total_xp': result[0] or 0,
                'level': result[1] or 1,
                'streak': result[2] or 0,
                'longest_streak': result[3] or 0,
                'experience': result[4] or 0,
                'translations': result[5] or 0,
                'books': result[6] or 0,
                'words': result[7] or 0
            }
        return {}
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {}


async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top users by XP"""
    try:
        sql.execute("""
            SELECT 
                l.user_id,
                ue.first_name,
                ue.username,
                l.total_xp,
                l.translations_count,
                l.words_learned,
                l.streak_days
            FROM leaderboard l
            JOIN users_enhanced ue ON l.user_id = ue.user_id
            ORDER BY l.total_xp DESC
            LIMIT %s
        """, (limit,))
        
        results = []
        for row in sql.fetchall():
            results.append({
                'user_id': row[0],
                'name': row[1] or row[2] or 'Anonymous',
                'username': row[2],
                'xp': row[3],
                'translations': row[4],
                'words': row[5],
                'streak': row[6]
            })
        return results
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return []
