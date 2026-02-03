"""
📊 Analytics Helper Functions
Easy-to-use functions for retrieving analytics data
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from config import sql


class UserAnalytics:
    """User-related analytics"""
    
    @staticmethod
    def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
        """Get comprehensive user profile"""
        sql.execute("""
            SELECT 
                u.*,
                (SELECT COUNT(*) FROM translation_history WHERE user_id = u.user_id) as total_translations,
                (SELECT COUNT(*) FROM vocab_books WHERE user_id = u.user_id) as total_books,
                (SELECT COUNT(*) FROM vocab_entries WHERE user_id = u.user_id) as total_vocab,
                (SELECT COUNT(*) FROM practice_sessions WHERE user_id = u.user_id) as total_exercises,
                (SELECT COALESCE(SUM(xp_earned), 0) FROM user_activity_daily WHERE user_id = u.user_id) as total_xp
            FROM users u
            WHERE u.user_id = %s
        """, (user_id,))
        
        row = sql.fetchone()
        if not row:
            return None
        
        return {
            'user_id': row[1],
            'first_name': row[2],
            'last_name': row[3],
            'username': row[4],
            'language_code': row[5],
            'interface_lang': row[8],
            'default_from_lang': row[9],
            'default_to_lang': row[10],
            'is_active': row[11],
            'is_blocked': row[12],
            'is_premium': row[13],
            'created_at': row[18],
            'last_activity_at': row[20],
            'source': row[22],
            'stats': {
                'total_translations': row[26],
                'total_books': row[27],
                'total_vocab': row[28],
                'total_exercises': row[29],
                'total_xp': row[30]
            }
        }
    
    @staticmethod
    def get_user_language_preferences(user_id: int) -> List[Dict[str, Any]]:
        """Get user's most used language pairs"""
        sql.execute("""
            SELECT 
                from_lang, to_lang,
                translation_count,
                total_characters,
                last_used_at
            FROM language_usage_stats
            WHERE user_id = %s
            ORDER BY translation_count DESC
        """, (user_id,))
        
        return [
            {
                'from_lang': row[0],
                'to_lang': row[1],
                'count': row[2],
                'characters': row[3],
                'last_used': row[4]
            }
            for row in sql.fetchall()
        ]
    
    @staticmethod
    def get_user_exercise_preferences(user_id: int) -> List[Dict[str, Any]]:
        """Get user's exercise type preferences"""
        sql.execute("""
            SELECT 
                exercise_type,
                session_count,
                total_questions,
                avg_accuracy,
                last_played_at,
                preference_score
            FROM exercise_type_stats
            WHERE user_id = %s
            ORDER BY preference_score DESC
        """, (user_id,))
        
        return [
            {
                'type': row[0],
                'sessions': row[1],
                'questions': row[2],
                'avg_accuracy': row[3],
                'last_played': row[4],
                'preference_score': row[5]
            }
            for row in sql.fetchall()
        ]
    
    @staticmethod
    def get_user_activity_timeline(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get user's daily activity timeline"""
        sql.execute("""
            SELECT 
                activity_date,
                translations_count,
                translation_chars,
                exercise_sessions_count,
                exercise_questions_count,
                exercise_correct_count,
                xp_earned,
                daily_streak
            FROM user_activity_daily
            WHERE user_id = %s AND activity_date > CURRENT_DATE - INTERVAL '%s days'
            ORDER BY activity_date DESC
        """, (user_id, days))
        
        return [
            {
                'date': row[0],
                'translations': row[1],
                'chars': row[2],
                'exercise_sessions': row[3],
                'questions': row[4],
                'correct': row[5],
                'xp': row[6],
                'streak': row[7]
            }
            for row in sql.fetchall()
        ]


class BotAnalytics:
    """Bot-wide analytics"""
    
    @staticmethod
    def get_overview_stats() -> Dict[str, Any]:
        """Get bot overview statistics"""
        sql.execute("SELECT COUNT(*) FROM users")
        total_users = sql.fetchone()[0]
        
        sql.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
        active_users = sql.fetchone()[0]
        
        sql.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
        new_users_today = sql.fetchone()[0]
        
        sql.execute("SELECT COUNT(*) FROM translation_history")
        total_translations = sql.fetchone()[0] or 0
        
        sql.execute("SELECT COUNT(*) FROM translation_history WHERE DATE(created_at) = CURRENT_DATE")
        translations_today = sql.fetchone()[0] or 0
        
        sql.execute("SELECT COUNT(*) FROM practice_sessions")
        total_exercises = sql.fetchone()[0] or 0
        
        sql.execute("SELECT COUNT(*) FROM vocab_entries")
        total_vocab = sql.fetchone()[0] or 0
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'new_today': new_users_today
            },
            'translations': {
                'total': total_translations,
                'today': translations_today
            },
            'exercises': total_exercises,
            'vocabulary': total_vocab
        }
    
    @staticmethod
    def get_growth_stats(days: int = 30) -> List[Dict[str, Any]]:
        """Get daily growth statistics"""
        sql.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as new_users
            FROM users
            WHERE created_at > CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (days,))
        
        user_growth = {row[0]: row[1] for row in sql.fetchall()}
        
        sql.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as translations
            FROM translation_history
            WHERE created_at > CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (days,))
        
        trans_growth = {row[0]: row[1] for row in sql.fetchall()}
        
        # Combine
        all_dates = set(user_growth.keys()) | set(trans_growth.keys())
        return [
            {
                'date': d,
                'new_users': user_growth.get(d, 0),
                'translations': trans_growth.get(d, 0)
            }
            for d in sorted(all_dates, reverse=True)
        ]
    
    @staticmethod
    def get_language_stats() -> List[Dict[str, Any]]:
        """Get most popular language pairs"""
        sql.execute("""
            SELECT 
                from_lang,
                to_lang,
                COUNT(*) as count
            FROM translation_history
            GROUP BY from_lang, to_lang
            ORDER BY count DESC
            LIMIT 20
        """)
        
        return [
            {
                'from_lang': row[0],
                'to_lang': row[1],
                'count': row[2]
            }
            for row in sql.fetchall()
        ]
    
    @staticmethod
    def get_top_users(limit: int = 100, metric: str = 'translations') -> List[Dict[str, Any]]:
        """Get top users by various metrics"""
        if metric == 'translations':
            sql.execute("""
                SELECT 
                    u.user_id,
                    u.first_name,
                    u.username,
                    COUNT(th.id) as count
                FROM users u
                LEFT JOIN translation_history th ON u.user_id = th.user_id
                GROUP BY u.user_id, u.first_name, u.username
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
        elif metric == 'exercises':
            sql.execute("""
                SELECT 
                    u.user_id,
                    u.first_name,
                    u.username,
                    COUNT(ps.id) as count
                FROM users u
                LEFT JOIN practice_sessions ps ON u.user_id = ps.user_id
                GROUP BY u.user_id, u.first_name, u.username
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
        elif metric == 'vocabulary':
            sql.execute("""
                SELECT 
                    u.user_id,
                    u.first_name,
                    u.username,
                    COUNT(ve.id) as count
                FROM users u
                LEFT JOIN vocab_entries ve ON u.user_id = ve.user_id
                GROUP BY u.user_id, u.first_name, u.username
                ORDER BY count DESC
                LIMIT %s
            """, (limit,))
        
        return [
            {
                'user_id': row[0],
                'first_name': row[1],
                'username': row[2],
                'count': row[3]
            }
            for row in sql.fetchall()
        ]
    
    @staticmethod
    def get_retention_stats() -> Dict[str, Any]:
        """Get user retention statistics"""
        # DAU (Daily Active Users)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM user_activity_daily 
            WHERE activity_date = CURRENT_DATE
        """)
        dau = sql.fetchone()[0] or 0
        
        # WAU (Weekly Active Users)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM user_activity_daily 
            WHERE activity_date > CURRENT_DATE - INTERVAL '7 days'
        """)
        wau = sql.fetchone()[0] or 0
        
        # MAU (Monthly Active Users)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM user_activity_daily 
            WHERE activity_date > CURRENT_DATE - INTERVAL '30 days'
        """)
        mau = sql.fetchone()[0] or 0
        
        # Return rate (users active in last 7 days who were also active 8-14 days ago)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) 
            FROM user_activity_daily 
            WHERE activity_date > CURRENT_DATE - INTERVAL '7 days'
            AND user_id IN (
                SELECT DISTINCT user_id 
                FROM user_activity_daily 
                WHERE activity_date BETWEEN CURRENT_DATE - INTERVAL '14 days' 
                AND CURRENT_DATE - INTERVAL '7 days'
            )
        """)
        returning_users = sql.fetchone()[0] or 0
        
        return {
            'dau': dau,
            'wau': wau,
            'mau': mau,
            'returning_users': returning_users,
            'stickiness': round(dau / mau * 100, 2) if mau > 0 else 0
        }


class ExerciseAnalytics:
    """Exercise and practice analytics"""
    
    @staticmethod
    def get_exercise_type_distribution() -> List[Dict[str, Any]]:
        """Get distribution of exercise types across all users"""
        sql.execute("""
            SELECT 
                exercise_type,
                SUM(session_count) as total_sessions,
                AVG(avg_accuracy) as avg_accuracy
            FROM exercise_type_stats
            GROUP BY exercise_type
            ORDER BY total_sessions DESC
        """)
        
        return [
            {
                'type': row[0],
                'total_sessions': row[1],
                'avg_accuracy': round(row[2], 2) if row[2] else 0
            }
            for row in sql.fetchall()
        ]
    
    @staticmethod
    def get_exercise_performance_stats(days: int = 30) -> Dict[str, Any]:
        """Get exercise performance statistics"""
        sql.execute("""
            SELECT 
                COUNT(*) as total_sessions,
                AVG(accuracy_percentage) as avg_accuracy,
                AVG(total_questions) as avg_questions,
                SUM(xp_earned) as total_xp
            FROM practice_sessions
            WHERE started_at > NOW() - INTERVAL '%s days'
        """, (days,))
        
        row = sql.fetchone()
        return {
            'total_sessions': row[0] or 0,
            'avg_accuracy': round(row[1], 2) if row[1] else 0,
            'avg_questions': round(row[2], 2) if row[2] else 0,
            'total_xp': row[3] or 0
        }


def generate_comprehensive_report(user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate comprehensive analytics report
    If user_id is provided, generates user-specific report
    Otherwise generates bot-wide report
    """
    if user_id:
        return {
            'profile': UserAnalytics.get_user_profile(user_id),
            'languages': UserAnalytics.get_user_language_preferences(user_id),
            'exercises': UserAnalytics.get_user_exercise_preferences(user_id),
            'timeline': UserAnalytics.get_user_activity_timeline(user_id)
        }
    else:
        return {
            'overview': BotAnalytics.get_overview_stats(),
            'growth': BotAnalytics.get_growth_stats(),
            'languages': BotAnalytics.get_language_stats(),
            'top_users': BotAnalytics.get_top_users(50),
            'retention': BotAnalytics.get_retention_stats(),
            'exercise_stats': ExerciseAnalytics.get_exercise_performance_stats()
        }
