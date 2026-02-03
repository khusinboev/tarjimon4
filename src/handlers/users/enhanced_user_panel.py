"""
👤 Enhanced User Panel for Tarjimon Bot
Sophisticated, feature-rich user interface with beautiful designs
"""

import asyncio
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from typing import Dict, Any, List

from config import sql, db, bot, ADMIN_ID, LANGUAGES
from src.keyboards.sophisticated_keyboards import (
    user_kb, lang_selector, practice_kb, game_kb,
    FancyButtons, VisualLanguageSelector
)
from src.db.enhanced_schema import get_user_stats, get_leaderboard

enhanced_user_router = Router()


# ==========================================
# 🎨 VISUAL HELPERS
# ==========================================

def create_progress_bar(current: int, total: int, length: int = 10) -> str:
    """Create visual progress bar"""
    percent = min(100, int(current / total * 100)) if total > 0 else 0
    filled = int(percent / 100 * length)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percent}%"


def format_number(num: int) -> str:
    """Format large numbers with K/M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def get_greeting(hour: int = None) -> str:
    """Get time-appropriate greeting"""
    if hour is None:
        hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "🌅 Xayrli tong"
    elif 12 <= hour < 17:
        return "☀️ Xayrli kun"
    elif 17 <= hour < 22:
        return "🌆 Xayrli oqshom"
    else:
        return "🌙 Xayrli tun"


# ==========================================
# 📱 MAIN MENU & START
# ==========================================

# Note: /start is handled by original users.py handler
# This file provides additional callback handlers and inline keyboards

async def enhanced_welcome(message: Message):
    """Enhanced welcome message - can be called by other handlers"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Register/update user in enhanced database
    try:
        sql.execute("""
            INSERT INTO users_enhanced (user_id, username, first_name, language_code)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_active_at = NOW()
        """, (user_id, username, first_name, message.from_user.language_code or 'uz'))
        db.commit()
    except Exception as e:
        print(f"User registration error: {e}")
    
    # Don't send a separate message, just ensure user is registered
    # The original /start handler will send the welcome message

# Additional command handlers for new features

@enhanced_user_router.message(Command("profile"))
async def cmd_profile(message: Message):
    """Show user profile"""
    # Reuse the profile_menu handler
    await profile_menu(message)


@enhanced_user_router.message(F.text == FancyButtons.PROFILE)
async def profile_button_handler(message: Message):
    """Handle profile button press"""
    await profile_menu(message)


# ==========================================
# 📝 TRANSLATION MENU
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.TRANSLATE)
async def translation_menu(message: Message):
    """Enhanced translation menu"""
    text = """
📝 <b>TARJIMA QILISH</b>

Quyidagi usullardan birini tanlang:

📝 <b>Matn</b> — Har qanday matnni tarjima qilish
🎙️ <b>Ovozli</b> — Ovozli xabarni matnga aylantirish
📷 <b>Rasm/OCR</b> — Rasmdagi matnni tanib olish
📎 <b>Hujjat</b> — PDF va hujjatlarni tarjima qilish

💡 <i>Matn yuborish uchun tilni tanlab, matnni yozing!</i>
"""
    await message.answer(text, reply_markup=user_kb.translation_menu(), parse_mode="HTML")


@enhanced_user_router.message(F.text == FancyButtons.LANGUAGES)
async def language_selection(message: Message):
    """Visual language selection"""
    user_id = message.from_user.id
    
    # Get current language preferences
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    result = sql.fetchone()
    current_from = result[0] if result else 'auto'
    current_to = result[1] if result else 'uz'
    
    text = f"""
🌐 <b>TILNI TANLASH</b>

Joriy sozlamalar:
📥 Manba: {VisualLanguageSelector.get_language_emoji(current_from)} <b>{LANGUAGES.get(current_from, {}).get('name', 'Avto-aniqlash')}</b>
📤 Maqsad: {VisualLanguageSelector.get_language_emoji(current_to)} <b>{LANGUAGES.get(current_to, {}).get('name', 'Tanlanmagan')}</b>

Yangi tilni tanlang yoki almashtiring:
"""
    
    await message.answer(
        text,
        reply_markup=lang_selector.dual_language_selector(user_id, current_from, current_to),
        parse_mode="HTML"
    )


# ==========================================
# 👤 PROFILE MENU
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.PROFILE)
async def profile_menu(message: Message):
    """Enhanced profile display"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Ensure user exists in enhanced database first
    try:
        sql.execute("""
            INSERT INTO users_enhanced (user_id, username, first_name, language_code, created_at, last_active_at)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
            ON CONFLICT (user_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_active_at = NOW()
        """, (user_id, username, first_name, message.from_user.language_code or 'uz'))
        db.commit()
        
        # Also ensure leaderboard entry exists
        sql.execute("""
            INSERT INTO leaderboard (user_id, total_xp)
            VALUES (%s, 0)
            ON CONFLICT (user_id) DO NOTHING
        """, (user_id,))
        db.commit()
    except Exception as e:
        print(f"User registration error: {e}")
    
    # Get user stats
    stats = await get_user_stats(user_id)
    
    # Get user info
    sql.execute("""
        SELECT first_name, username, is_premium, premium_until, streak_days, user_level, experience_points
        FROM users_enhanced WHERE user_id = %s
    """, (user_id,))
    user_info = sql.fetchone()
    
    if not user_info:
        # If still no user info, create default
        name = first_name or "Foydalanuvchi"
        is_premium = False
        streak = 0
        level = 1
        xp = 0
    else:
        name, username, is_premium, premium_until, streak, level, xp = user_info
    
    # Calculate XP for next level
    xp_for_next = level * 100
    xp_progress = xp % 100
    
    # Premium badge
    premium_badge = "💎 PREMIUM" if is_premium else "🆓 Standart"
    
    # Streak fire
    streak_display = f"🔥 {streak} kun" if streak > 0 else "❌ Yo'q"
    
    # Build username display
    username_display = '@' + username if username else "📵 Username yo'q"
    
    profile_text = f"""
👤 <b>PROFILIM</b>

🎭 <b>{name}</b>
{username_display}

🏅 <b>Status:</b> {premium_badge}
⭐ <b>Level:</b> {level}
💎 <b>XP:</b> {xp} / {xp_for_next}
{create_progress_bar(xp_progress, 100)}

🔥 <b>Izchillik:</b> {streak_display}
📊 <b>Tarjimalar:</b> {stats.get('translations', 0)}
📚 <b>Lug'atlar:</b> {stats.get('books', 0)}
📝 <b>So'zlar:</b> {stats.get('words', 0)}

📅 <b>Qo'shilgan:</b> {datetime.now().strftime('%d.%m.%Y')}
"""
    
    user_data = {
        'level': level,
        'xp': xp,
        'streak': streak
    }
    
    await message.answer(
        profile_text,
        reply_markup=user_kb.profile_menu(user_data),
        parse_mode="HTML"
    )


@enhanced_user_router.callback_query(F.data == "profile:detailed")
async def detailed_stats(callback: CallbackQuery):
    """Show detailed statistics"""
    user_id = callback.from_user.id
    
    # Get detailed stats
    sql.execute("""
        SELECT 
            COUNT(*) as total_trans,
            COUNT(CASE WHEN DATE(created_at) = CURRENT_DATE THEN 1 END) as today_trans,
            COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as week_trans,
            COUNT(DISTINCT from_lang || '→' || to_lang) as unique_pairs
        FROM translations_enhanced WHERE user_id = %s
    """, (user_id,))
    
    trans_stats = sql.fetchone()
    
    sql.execute("""
        SELECT 
            COUNT(*) as total_words,
            COUNT(DISTINCT book_id) as books_with_words
        FROM vocab_entries_enhanced ve
        JOIN vocab_books_enhanced vb ON ve.book_id = vb.id
        WHERE vb.user_id = %s
    """, (user_id,))
    
    vocab_stats = sql.fetchone()
    
    # study_sessions table may not exist, so use default values
    study_stats = (0, 0)  # (total_cards, avg_accuracy)
    
    text = f"""
📊 <b>BATAFSIL STATISTIKA</b>

🔄 <b>TARJIMALAR:</b>
├ Jami: <b>{trans_stats[0] or 0}</b>
├ Bugun: <b>{trans_stats[1] or 0}</b>
├ Haftalik: <b>{trans_stats[2] or 0}</b>
└ Turli tillar: <b>{trans_stats[3] or 0} juftlik</b>

📚 <b>LUG'ATLAR:</b>
├ Jami so'zlar: <b>{vocab_stats[0] or 0}</b>
└ Lug'atlar soni: <b>{vocab_stats[1] or 0}</b>

🏋️ <b>MASHQLAR:</b>
├ Karta soni: <b>{study_stats[0] or 0}</b>
└ O'rtacha natija: <b>{study_stats[1] or 0:.1f}%</b>

💡 <i>Har kuni mashq qilib, izchillikni oshiring!</i>
"""
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@enhanced_user_router.callback_query(F.data == "profile:leaderboard")
async def show_leaderboard(callback: CallbackQuery):
    """Show user leaderboard"""
    from src.utils.gamification import LeaderboardManager
    
    user_id = callback.from_user.id
    
    # Get top 10 users
    leaderboard = LeaderboardManager.get_leaderboard(10)
    
    text = "🏆 <b>REYTING — TOP 10</b>\n\n"
    
    for i, user in enumerate(leaderboard, 1):
        is_current = user['user_id'] == user_id
        prefix = "👉 " if is_current else "   "
        medals = {1: '🥇', 2: '🥈', 3: '🥉'}
        rank = medals.get(i, f"{i}.")
        
        name = user['name'][:15] + "..." if len(user['name']) > 15 else user['name']
        if is_current:
            name = "Siz"
        
        text += f"{prefix}{rank} <b>{name}</b> — {user['xp']} XP | L{user.get('level', 1)}\n"
    
    # Get user's rank
    my_rank = LeaderboardManager.get_user_rank(user_id)
    if my_rank.get('rank'):
        text += f"\n📊 <b>Siz:</b> #{my_rank['rank']} ({my_rank['xp']} XP)"
    
    text += "\n💪 <i>O'z reytingingizni oshiring!</i>"
    
    # Add refresh button
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=FancyButtons.REFRESH, callback_data="profile:leaderboard")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="profile:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_user_router.callback_query(F.data == "profile:achievements")
async def show_achievements_callback(callback: CallbackQuery):
    """Show user achievements from profile callback"""
    user_id = callback.from_user.id
    
    try:
        # Get user achievements - using safe column names
        sql.execute("""
            SELECT a.code, a.name, a.description, a.icon_emoji, a.rarity, a.xp_reward,
                   ua.unlocked_at, ua.progress
            FROM achievements a
            LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = %s
            ORDER BY ua.unlocked_at DESC NULLS LAST, a.xp_reward DESC
        """, (user_id,))
        
        achievements = []
        unlocked_count = 0
        total_xp = 0
        
        for row in sql.fetchall():
            is_unlocked = row[6] is not None
            if is_unlocked:
                unlocked_count += 1
                total_xp += row[5]
            
            achievements.append({
                'code': row[0],
                'name': row[1],
                'description': row[2],
                'icon': row[3],
                'rarity': row[4],
                'xp': row[5],
                'unlocked': is_unlocked,
                'unlocked_at': row[6],
                'progress': row[7] or 0
            })
        
        total_count = len(achievements)
        progress_percent = int(unlocked_count / total_count * 100) if total_count > 0 else 0
        
        text = f"""
🏆 <b>YUTUQLARIM</b>

{create_progress_bar(unlocked_count, total_count)} <b>{unlocked_count}/{total_count}</b>
💎 Jami to'plangan XP: <b>{total_xp}</b>

"""
        
        # Show all achievements
        for ach in achievements:
            status = "✅" if ach['unlocked'] else "🔒"
            rarity_emoji = {"common": "⚪", "rare": "🔵", "epic": "🟣", "legendary": "🟡"}.get(ach['rarity'], "⚪")
            text += f"{status} {ach['icon']} <b>{ach['name']}</b> {rarity_emoji}\n"
            text += f"   {ach['description']}\n"
            if ach['unlocked']:
                text += f"   🎁 +{ach['xp']} XP\n"
            text += "\n"
        
        # Add back button
        builder = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="profile:back")]
        ])
        
        await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
        await callback.answer()
        
    except Exception as e:
        print(f"[ERROR] show_achievements_callback: {e}")
        await callback.message.answer(
            "❌ Yutuqlarni yuklashda xatolik yuz berdi.\n"
            "❌ Error loading achievements.",
            parse_mode="HTML"
        )
        await callback.answer()


# ==========================================
# 📚 VOCABULARY MENU
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.VOCABULARY)
async def vocabulary_menu(message: Message):
    """Enhanced vocabulary menu"""
    text = """
📚 <b>LUG'ATLAR VA MASHQLAR</b>

So'z boyligingizni oshiring va yangi tillarni o'rganing!

📖 <b>Mening lug'atlarim</b> — Shaxsiy so'zlar to'plamingiz
🌐 <b>Ommaviy lug'atlar</b> — Boshqalar yaratgan to'plamlar
📚 <b>Essentiallar</b> — Asosiy so'zlar
🌍 <b>Parallel tarjimalar</b> — Kontekst bilan o'rganish
🏋️ <b>Mashqlar</b> — Bilimni mustahkamlash

🎯 <i>Bosqichma-bosqich til o'rganing!</i>
"""
    await message.answer(text, reply_markup=user_kb.vocabulary_menu(), parse_mode="HTML")


@enhanced_user_router.message(F.text == FancyButtons.PRACTICE)
async def practice_menu(message: Message):
    """Practice modes menu"""
    text = """
🏋️ <b>MASHQLAR</b>

O'z bilimingizni sinab ko'ring:

🎯 <b>Flashcards</b> — Tez ko'rib chiqish
✏️ <b>Yozma mashq</b> — Yodlashni mustahkamlash
🔤 <b>Tanlash</b> — Test shaklida
👂 <b>Tinglash</b> — Eshitish tushunish
⚡ <b>Tez mashq</b> — 5 daqiqalik intensiv
🎮 <b>O'yin</b> — Qiziqarli o'rganish

🚀 <i>Har kuni mashq qiling va izchillikni saqlang!</i>
"""
    await message.answer(text, reply_markup=practice_kb.practice_modes(), parse_mode="HTML")


# ==========================================
# ⚙️ SETTINGS MENU
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.SETTINGS)
async def settings_menu(message: Message):
    """Enhanced settings menu"""
    text = """
⚙️ <b>SOZLAMALAR</b>

Botni o'zingizga moslang:

🌐 <b>Til</b> — Interfeys tilini tanlash
🔔 <b>Bildirishnomalar</b> — Eslatmalar sozlamalari
🎨 <b>Mavzu</b> — Ko'rinishni o'zgartirish
🔊 <b>Ovoz</b> — Audio sozlamalari
📊 <b>Eksport</b> — Ma'lumotlaringizni yuklab olish
🗑️ <b>O'chirish</b> — Ma'lumotlarni tozalash

❓ <i>Yordam kerakmi? Qo'llanmani oching</i>
"""
    await message.answer(text, reply_markup=user_kb.settings_menu(), parse_mode="HTML")


# ==========================================
# 🏆 ACHIEVEMENTS
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.ACHIEVEMENTS)
async def achievements_menu(message: Message):
    """Show user achievements"""
    user_id = message.from_user.id
    
    # Get user achievements
    sql.execute("""
        SELECT a.code, a.name, a.description, a.icon_emoji, a.rarity, a.xp_reward,
               ua.unlocked_at, ua.progress
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = %s
        ORDER BY ua.unlocked_at DESC NULLS LAST, a.xp_reward DESC
    """, (user_id,))
    
    achievements = []
    unlocked_count = 0
    total_xp = 0
    
    for row in sql.fetchall():
        is_unlocked = row[6] is not None
        if is_unlocked:
            unlocked_count += 1
            total_xp += row[5]
        
        achievements.append({
            'code': row[0],
            'name': row[1],
            'description': row[2],
            'icon': row[3],
            'rarity': row[4],
            'xp': row[5],
            'unlocked': is_unlocked,
            'unlocked_at': row[6],
            'progress': row[7] or 0
        })
    
    total_count = len(achievements)
    progress_percent = int(unlocked_count / total_count * 100) if total_count > 0 else 0
    
    text = f"""
🏆 <b>YUTUQLAR</b>

{create_progress_bar(unlocked_count, total_count)} <b>{unlocked_count}/{total_count}</b>
💎 Jami to'plangan XP: <b>{total_xp}</b>

"""
    
    # Show recent achievements
    recent = [a for a in achievements if a['unlocked']][:3]
    if recent:
        text += "✨ <b>Yaqinda olingan:</b>\n"
        for ach in recent:
            text += f"  {ach['icon']} <b>{ach['name']}</b> (+{ach['xp']} XP)\n"
    else:
        text += "🔒 <i>Hali yutuq yo'q. Mashq qilishni boshlang!</i>\n"
    
    text += "\n🎯 <i>Barcha yutuqlarni ko'rish uchun bosing:</i>"
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Barcha yutuqlar", callback_data="ach:all")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="ach:back")]
    ])
    
    await message.answer(text, reply_markup=builder, parse_mode="HTML")


# ==========================================
# 🎯 DAILY CHALLENGE
# ==========================================

@enhanced_user_router.callback_query(F.data == "profile:daily")
async def daily_challenge(callback: CallbackQuery):
    """Show daily challenge"""
    user_id = callback.from_user.id
    
    # Get or create today's challenge
    sql.execute("""
        SELECT id, title, description, challenge_type, target_value, xp_reward
        FROM daily_challenges WHERE DATE(created_at) = CURRENT_DATE
        LIMIT 1
    """)
    
    challenge = sql.fetchone()
    
    if not challenge:
        # Create default challenge
        challenge = (0, "🎯 Kunlik vazifa", "5 ta so'zni o'rganing", "words", 5, 50)
    
    # Get user progress
    sql.execute("""
        SELECT current_value, is_completed
        FROM user_challenge_progress
        WHERE user_id = %s AND challenge_id = %s
    """, (user_id, challenge[0]))
    
    progress = sql.fetchone()
    current = progress[0] if progress else 0
    completed = progress[1] if progress else False
    
    challenge_data = {
        'title': challenge[1],
        'description': challenge[2],
        'target': challenge[4],
        'current': current,
        'completed': completed,
        'reward': challenge[5]
    }
    
    text = f"""
🎯 <b>KUNLIK VAZIFA</b>

<b>{challenge_data['title']}</b>
{challenge_data['description']}

{create_progress_bar(current, challenge_data['target'])}
<b>{current}/{challenge_data['target']}</b>

🎁 Mukofot: <b>+{challenge_data['reward']} XP</b>
"""
    
    await callback.message.edit_text(
        text,
        reply_markup=game_kb.daily_challenge(challenge_data),
        parse_mode="HTML"
    )
    await callback.answer()


# ==========================================
# ℹ️ HELP MENU
# ==========================================

@enhanced_user_router.message(F.text == FancyButtons.HELP)
async def help_menu(message: Message):
    """Enhanced help menu"""
    text = """
ℹ️ <b>YORDAM MARKAZI</b>

<b>Asosiy buyruqlar:</b>
/start — Bosh menyu
/lang — Tilni tanlash
/history — Tarjima tarixi
/stats — Shaxsiy statistika
/cabinet — Lug'atlar kabineti

<b>Qo'shimcha imkoniyatlar:</b>
• Matn yuboring → Avto tarjima
• Rasm yuboring → Caption tarjima
• Ovoz yuboring → Audio tanib olish

<b>Bog'lanish:</b>
Muammolar uchun: @adkhambek_4
"""
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Qo'llanma", url="https://t.me/tarjimon_news")],
        [InlineKeyboardButton(text="💬 Qo'llab-quvvatlash", url="https://t.me/adkhambek_4")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="help:back")]
    ])
    
    await message.answer(text, reply_markup=builder, parse_mode="HTML")


# ==========================================
# 🔄 CALLBACK HANDLERS
# ==========================================

@enhanced_user_router.callback_query(F.data == "profile:back")
async def back_to_profile(callback: CallbackQuery):
    """Go back to profile"""
    await profile_menu(callback.message)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


@enhanced_user_router.callback_query(F.data == "vocab:back")
async def back_from_vocab(callback: CallbackQuery):
    """Go back from vocabulary"""
    await callback.message.delete()
    await callback.answer()


@enhanced_user_router.callback_query(F.data.startswith("lang:set:"))
async def set_language(callback: CallbackQuery):
    """Handle language selection"""
    _, _, direction, lang_code = callback.data.split(":")
    user_id = callback.from_user.id
    
    # Update database
    try:
        field = "from_lang" if direction == "from" else "to_lang"
        sql.execute(f"""
            INSERT INTO user_languages (user_id, {field})
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET {field} = EXCLUDED.{field}
        """, (user_id, lang_code))
        db.commit()
    except Exception as e:
        print(f"Language update error: {e}")
    
    # Refresh the keyboard
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    result = sql.fetchone()
    current_from = result[0] if result else 'auto'
    current_to = result[1] if result else 'uz'
    
    await callback.message.edit_reply_markup(
        reply_markup=lang_selector.dual_language_selector(user_id, current_from, current_to)
    )
    await callback.answer("✅ Til yangilandi!")


@enhanced_user_router.callback_query(F.data == "lang:switch")
async def switch_languages(callback: CallbackQuery):
    """Switch source and target languages"""
    user_id = callback.from_user.id
    
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    result = sql.fetchone()
    
    if result:
        from_lang, to_lang = result
        # Don't switch if source is auto
        if from_lang != 'auto':
            sql.execute("""
                UPDATE user_languages 
                SET from_lang = %s, to_lang = %s 
                WHERE user_id = %s
            """, (to_lang, from_lang, user_id))
            db.commit()
            
            await callback.message.edit_reply_markup(
                reply_markup=lang_selector.dual_language_selector(user_id, to_lang, from_lang)
            )
    
    await callback.answer("🔄 Tillar almashtirildi!")


@enhanced_user_router.callback_query(F.data == "lang:done")
async def language_selection_done(callback: CallbackQuery):
    """Finish language selection"""
    await callback.message.delete()
    await callback.answer("✅ Sozlamalar saqlandi!")
    
    # Show confirmation
    user_id = callback.from_user.id
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    result = sql.fetchone()
    
    if result:
        from_lang, to_lang = result
        from_name = LANGUAGES.get(from_lang, {}).get('name', 'Avto') if from_lang != 'auto' else 'Avto-aniqlash'
        to_name = LANGUAGES.get(to_lang, {}).get('name', 'Tanlanmagan')
        
        await callback.message.answer(
            f"🌐 <b>Tillar sozlandi:</b>\n\n"
            f"📥 {from_name} → 📤 {to_name}\n\n"
            f"Endi matn yuborishingiz mumkin! ✨",
            parse_mode="HTML"
        )
