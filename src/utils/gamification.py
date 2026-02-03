"""
🎮 Gamification System for Tarjimon Bot
XP, achievements, leaderboards, and engagement features
PostgreSQL version
"""

import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from config import sql, db


@dataclass
class XPRewards:
    """XP rewards for different actions"""
    TRANSLATION = 5
    TRANSLATION_VOICE = 10
    VOCAB_ADD = 3
    VOCAB_BOOK_CREATE = 20
    PRACTICE_CORRECT = 5
    PRACTICE_COMPLETE = 25
    DAILY_STREAK = 50
    ACHIEVEMENT_UNLOCK = 100
    SOCIAL_SHARE = 15
    FEEDBACK_SUBMIT = 10


class GamificationEngine:
    """🏆 Core gamification engine"""
    
    # Level thresholds
    LEVEL_THRESHOLDS = [
        0,      # Level 1
        100,    # Level 2
        300,    # Level 3
        600,    # Level 4
        1000,   # Level 5
        1500,   # Level 6
        2100,   # Level 7
        2800,   # Level 8
        3600,   # Level 9
        4500,   # Level 10
        5500,   # Level 11
        6600,   # Level 12
        7800,   # Level 13
        9100,   # Level 14
        10500,  # Level 15
        12000,  # Level 16
        13600,  # Level 17
        15300,  # Level 18
        17100,  # Level 19
        19000,  # Level 20
    ]
    
    @classmethod
    def calculate_level(cls, xp: int) -> int:
        """Calculate user level from XP"""
        for level, threshold in enumerate(cls.LEVEL_THRESHOLDS, 1):
            if xp < threshold:
                return max(1, level - 1)
        return len(cls.LEVEL_THRESHOLDS)
    
    @classmethod
    def xp_for_next_level(cls, current_level: int) -> int:
        """Get XP needed for next level"""
        if current_level < len(cls.LEVEL_THRESHOLDS):
            return cls.LEVEL_THRESHOLDS[current_level]
        return cls.LEVEL_THRESHOLDS[-1] + (current_level - len(cls.LEVEL_THRESHOLDS)) * 2000
    
    @classmethod
    def add_xp(cls, user_id: int, amount: int, reason: str = "") -> Dict[str, Any]:
        """Add XP to user and handle level ups"""
        try:
            # Check if user exists in enhanced table
            sql.execute("SELECT user_id FROM users_enhanced WHERE user_id = %s", (user_id,))
            if not sql.fetchone():
                # Create user if not exists
                sql.execute("""
                    INSERT INTO users_enhanced 
                    (user_id, username, first_name, language_code, created_at, last_active_at, experience_points, user_level)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), 0, 1)
                """, (user_id, None, None, 'uz'))
            
            # Ensure leaderboard entry exists
            sql.execute("SELECT user_id FROM leaderboard WHERE user_id = %s", (user_id,))
            if not sql.fetchone():
                sql.execute("INSERT INTO leaderboard (user_id, total_xp) VALUES (%s, 0)", (user_id,))
            
            db.commit()
            
            # Get current stats
            sql.execute("""
                SELECT experience_points, user_level, streak_days
                FROM users_enhanced WHERE user_id = %s
            """, (user_id,))
            
            result = sql.fetchone()
            if not result:
                return {"success": False, "error": "User not found"}
            
            current_xp, current_level, streak = result
            new_xp = current_xp + amount
            
            # Calculate new level
            new_level = cls.calculate_level(new_xp)
            level_up = new_level > current_level
            
            # Update database
            sql.execute("""
                UPDATE users_enhanced 
                SET experience_points = %s, user_level = %s, updated_at = NOW()
                WHERE user_id = %s
            """, (new_xp, new_level, user_id))
            
            # Update leaderboard
            sql.execute("""
                UPDATE leaderboard 
                SET total_xp = %s, last_updated = NOW()
                WHERE user_id = %s
            """, (new_xp, user_id))
            
            db.commit()
            
            return {
                "success": True,
                "xp_added": amount,
                "total_xp": new_xp,
                "new_level": new_level,
                "level_up": level_up,
                "reason": reason
            }
        except Exception as e:
            print(f"[ERROR] add_xp: {e}")
            db.rollback()
            return {"success": False, "error": str(e)}
    
    @classmethod
    def check_streak(cls, user_id: int) -> Dict[str, Any]:
        """Check and update user's daily streak"""
        try:
            # Get or create user
            sql.execute("SELECT user_id FROM users_enhanced WHERE user_id = %s", (user_id,))
            if not sql.fetchone():
                sql.execute("""
                    INSERT INTO users_enhanced 
                    (user_id, username, first_name, language_code, created_at, last_active_at, streak_days, last_streak_date)
                    VALUES (%s, %s, %s, %s, NOW(), NOW(), 1, CURRENT_DATE)
                """, (user_id, None, None, 'uz'))
                db.commit()
                return {
                    "success": True,
                    "streak": 1,
                    "maintained": False,
                    "xp_reward": 50
                }
            
            sql.execute("""
                SELECT streak_days, last_streak_date, longest_streak
                FROM users_enhanced WHERE user_id = %s
            """, (user_id,))
            
            result = sql.fetchone()
            if not result:
                return {"success": False, "error": "User not found"}
            
            streak, last_date, longest = result
            today = datetime.now().date()
            
            if last_date:
                # Parse date from string
                if isinstance(last_date, str):
                    last_date = datetime.strptime(last_date, '%Y-%m-%d').date()
                days_diff = (today - last_date).days
                
                if days_diff == 0:
                    # Already checked in today
                    return {
                        "success": True,
                        "streak": streak,
                        "maintained": True,
                        "xp_reward": 0
                    }
                elif days_diff == 1:
                    # Streak maintained
                    streak += 1
                    longest = max(longest or 0, streak)
                    xp_reward = min(50 + (streak * 5), 200)  # Cap at 200 XP
                else:
                    # Streak broken
                    streak = 1
                    xp_reward = 50
            else:
                streak = 1
                xp_reward = 50
            
            # Update database
            sql.execute("""
                UPDATE users_enhanced 
                SET streak_days = %s, longest_streak = %s, last_streak_date = CURRENT_DATE
                WHERE user_id = %s
            """, (streak, longest, user_id))
            
            db.commit()
            
            # Add XP for streak
            xp_result = cls.add_xp(user_id, xp_reward, f"Daily streak: {streak} days")
            
            return {
                "success": True,
                "streak": streak,
                "longest_streak": longest,
                "maintained": days_diff == 1 if last_date else False,
                "xp_reward": xp_reward,
                "level_up": xp_result.get("level_up", False)
            }
        except Exception as e:
            print(f"[ERROR] check_streak: {e}")
            return {"success": False, "error": str(e)}


class AchievementManager:
    """🏆 Achievement management system"""
    
    @staticmethod
    def check_achievements(user_id: int) -> List[Dict[str, Any]]:
        """Check and award new achievements for user"""
        unlocked = []
        
        try:
            # Get user stats
            sql.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM translations_enhanced WHERE user_id = %s) as translations_count,
                    (SELECT COUNT(*) FROM vocab_books_enhanced WHERE user_id = %s) as vocab_books_count,
                    (SELECT COUNT(*) FROM vocab_entries_enhanced ve 
                     JOIN vocab_books_enhanced vb ON ve.book_id = vb.id 
                     WHERE vb.user_id = %s) as words_count,
                    (SELECT streak_days FROM users_enhanced WHERE user_id = %s) as streak_days,
                    (SELECT COUNT(*) FROM practice_sessions WHERE user_id = %s) as practice_sessions
            """, (user_id, user_id, user_id, user_id, user_id))
            
            stats = sql.fetchone()
            if not stats:
                return []
            
            trans_count, books_count, words_count, streak, practice = stats
            
            # Get all achievements
            sql.execute("""
                SELECT id, code, requirement_type, requirement_value, xp_reward
                FROM achievements
            """)
            
            achievements = sql.fetchall()
            
            # Get already unlocked
            sql.execute("""
                SELECT achievement_id FROM user_achievements WHERE user_id = %s
            """, (user_id,))
            
            unlocked_ids = {row[0] for row in sql.fetchall()}
            
            for ach_id, code, req_type, req_value, xp_reward in achievements:
                if ach_id in unlocked_ids:
                    continue
                
                # Check if requirement met
                met = False
                progress = 0
                
                if req_type == 'translations_count':
                    progress = trans_count
                    met = trans_count >= req_value
                elif req_type == 'vocab_books_count':
                    progress = books_count
                    met = books_count >= req_value
                elif req_type == 'words_count':
                    progress = words_count
                    met = words_count >= req_value
                elif req_type == 'streak_days':
                    progress = streak or 0
                    met = (streak or 0) >= req_value
                elif req_type == 'practice_sessions':
                    progress = practice
                    met = practice >= req_value
                
                if met:
                    # Award achievement
                    sql.execute("""
                        INSERT INTO user_achievements (user_id, achievement_id, unlocked_at, progress)
                        VALUES (%s, %s, NOW(), %s)
                    """, (user_id, ach_id, progress))
                    
                    db.commit()
                    
                    # Add XP
                    GamificationEngine.add_xp(user_id, xp_reward, f"Achievement unlocked: {code}")
                    
                    unlocked.append({
                        "achievement_id": ach_id,
                        "code": code,
                        "xp_reward": xp_reward
                    })
            
            return unlocked
        except Exception as e:
            print(f"[ERROR] Achievement check error: {e}")
            return []


class DailyChallengeManager:
    """🎯 Daily challenge system"""
    
    CHALLENGE_TEMPLATES = [
        {"title": "📝 Tarjima ustasi", "type": "translations", "base_target": 5},
        {"title": "📚 So'z o'rganuvchi", "type": "words", "base_target": 10},
        {"title": "🏋️ Mashq qiluvchi", "type": "practice", "base_target": 3},
        {"title": "🔥 Izchillik saquvchi", "type": "streak", "base_target": 1},
        {"title": "🌐 Ko'p tillik", "type": "languages", "base_target": 3},
    ]
    
    @classmethod
    def generate_daily_challenge(cls) -> Optional[Dict[str, Any]]:
        """Generate new daily challenge"""
        try:
            # Check if today's challenge exists
            sql.execute("SELECT id FROM daily_challenges WHERE challenge_date = CURRENT_DATE")
            if sql.fetchone():
                return None
            
            # Generate random challenge
            template = random.choice(cls.CHALLENGE_TEMPLATES)
            target = template["base_target"] + random.randint(0, 5)
            
            descriptions = {
                "translations": f"Bugun {target} ta tarjima qiling",
                "words": f"Bugun {target} ta yangi so'z qo'shing",
                "practice": f"Bugun {target} ta mashq bajaring",
                "streak": "Bugun ham botdan foydalaning",
                "languages": f"Bugun {target} ta turli tilga tarjima qiling",
            }
            
            sql.execute("""
                INSERT INTO daily_challenges 
                (challenge_date, title, description, challenge_type, target_value, xp_reward)
                VALUES (CURRENT_DATE, %s, %s, %s, %s, %s)
            """, (
                template["title"],
                descriptions[template["type"]],
                template["type"],
                target,
                50 + (target * 5)
            ))
            
            db.commit()
            return {"success": True}
        except Exception as e:
            print(f"[ERROR] generate_daily_challenge: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    def get_user_challenge(cls, user_id: int) -> Dict[str, Any]:
        """Get today's challenge for user"""
        try:
            sql.execute("""
                SELECT dc.id, dc.title, dc.description, dc.challenge_type, 
                       dc.target_value, dc.xp_reward,
                       COALESCE(udc.current_value, 0) as current,
                       COALESCE(udc.is_completed, FALSE) as completed
                FROM daily_challenges dc
                LEFT JOIN user_daily_challenges udc 
                    ON dc.id = udc.challenge_id AND udc.user_id = %s
                WHERE dc.challenge_date = CURRENT_DATE
            """, (user_id,))
            
            result = sql.fetchone()
            if not result:
                return {"success": False, "error": "No challenge for today"}
            
            return {
                "success": True,
                "id": result[0],
                "title": result[1],
                "description": result[2],
                "type": result[3],
                "target": result[4],
                "reward": result[5],
                "current": result[6],
                "completed": result[7],
                "progress": min(100, int(result[6] / result[4] * 100))
            }
        except Exception as e:
            print(f"[ERROR] get_user_challenge: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    def update_progress(cls, user_id: int, challenge_type: str, amount: int = 1):
        """Update challenge progress for user"""
        try:
            sql.execute("""
                SELECT dc.id, dc.target_value, dc.xp_reward
                FROM daily_challenges dc
                WHERE dc.challenge_date = CURRENT_DATE AND dc.challenge_type = %s
            """, (challenge_type,))
            
            result = sql.fetchone()
            if not result:
                return {"success": False}
            
            challenge_id, target, reward = result
            
            # Get current progress
            sql.execute("""
                SELECT current_value FROM user_daily_challenges
                WHERE user_id = %s AND challenge_id = %s
            """, (user_id, challenge_id))
            
            progress_result = sql.fetchone()
            if progress_result:
                current = min(progress_result[0] + amount, target)
                sql.execute("""
                    UPDATE user_daily_challenges
                    SET current_value = %s
                    WHERE user_id = %s AND challenge_id = %s
                """, (current, user_id, challenge_id))
            else:
                current = amount
                sql.execute("""
                    INSERT INTO user_daily_challenges (user_id, challenge_id, current_value)
                    VALUES (%s, %s, %s)
                """, (user_id, challenge_id, current))
            
            # Check completion
            if current >= target:
                sql.execute("""
                    UPDATE user_daily_challenges
                    SET is_completed = TRUE, completed_at = NOW()
                    WHERE user_id = %s AND challenge_id = %s AND is_completed = FALSE
                """, (user_id, challenge_id))
                
                if sql.rowcount > 0:
                    # Award XP
                    GamificationEngine.add_xp(user_id, reward, "Daily challenge completed")
            
            db.commit()
            return {"success": True, "current": current, "target": target}
        except Exception as e:
            print(f"[ERROR] update_progress: {e}")
            return {"success": False, "error": str(e)}


class LeaderboardManager:
    """🥇 Leaderboard management"""
    
    @staticmethod
    def update_rankings():
        """Recalculate all rankings"""
        try:
            # Get all users ordered by XP
            sql.execute("SELECT user_id, total_xp FROM leaderboard ORDER BY total_xp DESC")
            users = sql.fetchall()
            
            # Update ranks
            for rank, (user_id, _) in enumerate(users, 1):
                sql.execute("""
                    UPDATE leaderboard
                    SET current_rank = %s,
                        highest_rank = LEAST(COALESCE(highest_rank, %s), %s),
                        last_updated = NOW()
                    WHERE user_id = %s
                """, (rank, rank, rank, user_id))
            
            db.commit()
            return {"success": True}
        except Exception as e:
            print(f"[ERROR] update_rankings: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_leaderboard(limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """Get global leaderboard"""
        try:
            sql.execute("""
                SELECT l.current_rank, l.user_id, ue.first_name, ue.username,
                       l.total_xp, ue.user_level, l.streak_days
                FROM leaderboard l
                JOIN users_enhanced ue ON l.user_id = ue.user_id
                ORDER BY l.total_xp DESC
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            results = []
            for row in sql.fetchall():
                results.append({
                    "rank": row[0] or 0,
                    "user_id": row[1],
                    "name": row[2] or row[3] or "Anonymous",
                    "username": row[3],
                    "xp": row[4],
                    "level": row[5] or 1,
                    "streak": row[6] or 0
                })
            
            return results
        except Exception as e:
            print(f"[ERROR] get_leaderboard: {e}")
            return []
    
    @staticmethod
    def get_user_rank(user_id: int) -> Dict[str, Any]:
        """Get user's ranking info"""
        try:
            sql.execute("""
                SELECT current_rank, total_xp
                FROM leaderboard WHERE user_id = %s
            """, (user_id,))
            
            result = sql.fetchone()
            if not result:
                return {"rank": None, "xp": 0}
            
            # Get total users
            sql.execute("SELECT COUNT(*) FROM leaderboard")
            total = sql.fetchone()[0]
            
            return {
                "rank": result[0],
                "xp": result[1],
                "total_users": total,
                "percentile": (1 - result[0] / total) * 100 if total > 0 and result[0] else 0
            }
        except Exception as e:
            print(f"[ERROR] get_user_rank: {e}")
            return {"rank": None, "xp": 0, "error": str(e)}


# Convenience functions
def award_translation_xp(user_id: int, text_length: int):
    """Award XP for translation"""
    base_xp = XPRewards.TRANSLATION
    bonus = min(text_length // 100, 10)  # Max 10 bonus XP
    return GamificationEngine.add_xp(user_id, base_xp + bonus, "Translation completed")


def award_practice_xp(user_id: int, correct_count: int, total_count: int):
    """Award XP for practice session"""
    accuracy = correct_count / total_count if total_count > 0 else 0
    base_xp = XPRewards.PRACTICE_COMPLETE
    bonus = int(correct_count * XPRewards.PRACTICE_CORRECT * accuracy)
    return GamificationEngine.add_xp(user_id, base_xp + bonus, "Practice completed")


def check_user_achievements(user_id: int) -> List[Dict]:
    """Check and award achievements"""
    return AchievementManager.check_achievements(user_id)
