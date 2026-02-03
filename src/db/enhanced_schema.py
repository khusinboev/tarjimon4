"""
🗄️ Enhanced Database Schema for Tarjimon Bot
PostgreSQL version
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
        
        # ==========================================
        # 2️⃣ TRANSLATION SYSTEM
        # ==========================================
        
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
                context JSONB DEFAULT '{}'::jsonb
            )
        """)
        
        # ==========================================
        # 3️⃣ VOCABULARY & LEARNING SYSTEM
        # ==========================================
        
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
                meta JSONB DEFAULT '{}'::jsonb
            )
        """)
        
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
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # ==========================================
        # 4️⃣ ACHIEVEMENTS & GAMIFICATION
        # ==========================================
        
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
        
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_achievements (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                achievement_id INTEGER NOT NULL,
                unlocked_at TIMESTAMP DEFAULT NOW(),
                progress INTEGER DEFAULT 0,
                is_claimed BOOLEAN DEFAULT FALSE,
                claimed_at TIMESTAMP,
                UNIQUE(user_id, achievement_id)
            )
        """)
        
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
        
        sql.execute("""
            CREATE TABLE IF NOT EXISTS user_daily_challenges (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                challenge_id INTEGER NOT NULL,
                current_value INTEGER DEFAULT 0,
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                UNIQUE(user_id, challenge_id)
            )
        """)
        
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
                last_updated TIMESTAMP DEFAULT NOW()
            )
        """)
        
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


# Helper functions for common operations
async def get_user_stats(user_id: int) -> Dict[str, Any]:
    """Get comprehensive user statistics"""
    try:
        sql.execute("""
            SELECT 
                (SELECT COUNT(*) FROM translations_enhanced WHERE user_id = %s) as translations_count,
                (SELECT COUNT(*) FROM vocab_books_enhanced WHERE user_id = %s) as vocab_books_count,
                (SELECT COUNT(*) FROM vocab_entries_enhanced ve 
                 JOIN vocab_books_enhanced vb ON ve.book_id = vb.id 
                 WHERE vb.user_id = %s) as words_count
        """, (user_id, user_id, user_id))
        
        row = sql.fetchone()
        if row:
            return {
                'translations': row[0] or 0,
                'books': row[1] or 0,
                'words': row[2] or 0
            }
        return {'translations': 0, 'books': 0, 'words': 0}
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {'translations': 0, 'books': 0, 'words': 0}


async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top users by XP"""
    try:
        sql.execute("""
            SELECT l.user_id, ue.first_name, ue.username, l.total_xp
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
                'xp': row[3]
            })
        return results
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return []
