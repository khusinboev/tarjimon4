"""
Translation history management
"""
from typing import List, Tuple, Optional
from datetime import datetime
from config import sql, db


def save_translation_history(
    user_id: int,
    from_lang: str,
    to_lang: str,
    original_text: str,
    translated_text: str
):
    """
    Tarjima tarixini saqlash
    
    Args:
        user_id: Foydalanuvchi ID
        from_lang: Qaysi tildan
        to_lang: Qaysi tilga
        original_text: Asl matn
        translated_text: Tarjima qilingan matn
    """
    try:
        # Table allaqachon comprehensive_schema.py da yaratilgan
        # Shuning uchun biz faqat INSERT qilamiz
        
        # Index yaratish (agar yo'q bo'lsa)
        sql.execute("""
            CREATE INDEX IF NOT EXISTS idx_translation_history_user_id 
            ON translation_history(user_id)
        """)
        
        sql.execute("""
            CREATE INDEX IF NOT EXISTS idx_translation_history_created_at 
            ON translation_history(created_at DESC)
        """)
        
        db.commit()
        
        # Tarjimani saqlash (comprehensive_schema ga muvofiq)
        sql.execute("""
            INSERT INTO translation_history 
            (user_id, from_lang, to_lang, source_text, translated_text)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, from_lang, to_lang, original_text[:1000], translated_text[:1000]))
        
        db.commit()
        
        # Eski tarixni tozalash (oxirgi 100tadan ko'pini o'chirish)
        sql.execute("""
            DELETE FROM translation_history
            WHERE id IN (
                SELECT id FROM translation_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                OFFSET 100
            )
        """, (user_id,))
        
        db.commit()
        
    except Exception as e:
        print(f"[ERROR] Failed to save translation history: {e}")
        db.rollback()


def get_translation_history(
    user_id: int,
    limit: int = 10
) -> List[Tuple[int, str, str, str, str, datetime]]:
    """
    Tarjima tarixini olish
    
    Args:
        user_id: Foydalanuvchi ID
        limit: Nechta tarjima olish
        
    Returns:
        List of (id, from_lang, to_lang, source_text, translated_text, created_at)
    """
    try:
        sql.execute("""
            SELECT id, from_lang, to_lang, source_text, translated_text, created_at
            FROM translation_history
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """, (user_id, limit))
        
        return sql.fetchall()
    except Exception as e:
        print(f"[ERROR] Failed to get translation history: {e}")
        return []


def get_favorite_translations(user_id: int) -> List[Tuple[int, str, str, str, str]]:
    """
    Sevimli tarjimalarni olish
    
    Args:
        user_id: Foydalanuvchi ID
        
    Returns:
        List of (id, from_lang, to_lang, source_text, translated_text)
    """
    try:
        sql.execute("""
            SELECT id, from_lang, to_lang, source_text, translated_text
            FROM translation_history
            WHERE user_id = %s AND is_favorite = TRUE
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id,))
        
        return sql.fetchall()
    except Exception as e:
        print(f"[ERROR] Failed to get favorite translations: {e}")
        return []


def toggle_favorite(user_id: int, translation_id: int) -> bool:
    """
    Tarjimani sevimliga qo'shish/olib tashlash
    
    Args:
        user_id: Foydalanuvchi ID
        translation_id: Tarjima ID
        
    Returns:
        True if success, False otherwise
    """
    try:
        sql.execute("""
            UPDATE translation_history
            SET is_favorite = NOT is_favorite
            WHERE id = %s AND user_id = %s
        """, (translation_id, user_id))
        
        db.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to toggle favorite: {e}")
        db.rollback()
        return False


def delete_translation(user_id: int, translation_id: int) -> bool:
    """
    Tarjimani o'chirish
    
    Args:
        user_id: Foydalanuvchi ID
        translation_id: Tarjima ID
        
    Returns:
        True if success, False otherwise
    """
    try:
        sql.execute("""
            DELETE FROM translation_history
            WHERE id = %s AND user_id = %s
        """, (translation_id, user_id))
        
        db.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to delete translation: {e}")
        db.rollback()
        return False


def clear_history(user_id: int) -> bool:
    """
    Barcha tarixni tozalash
    
    Args:
        user_id: Foydalanuvchi ID
        
    Returns:
        True if success, False otherwise
    """
    try:
        sql.execute("""
            DELETE FROM translation_history
            WHERE user_id = %s AND is_favorite = FALSE
        """, (user_id,))
        
        db.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to clear history: {e}")
        db.rollback()
        return False


def get_user_translation_stats(user_id: int) -> dict:
    """
    Foydalanuvchi tarjima statistikasini olish
    
    Args:
        user_id: Foydalanuvchi ID
        
    Returns:
        Dictionary with stats
    """
    try:
        # Jami tarjimalar
        sql.execute("""
            SELECT COUNT(*) FROM translation_history
            WHERE user_id = %s
        """, (user_id,))
        total = sql.fetchone()[0]
        
        # Eng ko'p ishlatiladigan til juftligi
        sql.execute("""
            SELECT from_lang, to_lang, COUNT(*) as count
            FROM translation_history
            WHERE user_id = %s
            GROUP BY from_lang, to_lang
            ORDER BY count DESC
            LIMIT 1
        """, (user_id,))
        
        most_used = sql.fetchone()
        
        # Bugungi tarjimalar
        sql.execute("""
            SELECT COUNT(*) FROM translation_history
            WHERE user_id = %s AND DATE(created_at) = CURRENT_DATE
        """, (user_id,))
        today = sql.fetchone()[0]
        
        return {
            "total": total,
            "today": today,
            "most_used": most_used if most_used else None
        }
    except Exception as e:
        print(f"[ERROR] Failed to get stats: {e}")
        return {"total": 0, "today": 0, "most_used": None}
