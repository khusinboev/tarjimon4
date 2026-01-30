"""
👨‍💼 Enhanced Admin Panel for Tarjimon Bot
Advanced analytics, user management, and system control
"""

import asyncio
import io
import csv
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from config import sql, db, bot, ADMIN_ID, DB_CONFIG
from src.keyboards.sophisticated_keyboards import admin_kb, FancyButtons

enhanced_admin_router = Router()


# ==========================================
# 📊 STATES
# ==========================================

class AdminStates(StatesGroup):
    broadcast_message = State()
    broadcast_target = State()
    user_search = State()
    system_config = State()
    achievement_edit = State()


# ==========================================
# 🔐 ADMIN ACCESS DECORATOR
# ==========================================

def admin_only(handler):
    """Decorator to ensure only admins can access"""
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in ADMIN_ID:
            await message.answer("⛔ Sizga ruxsat yo'q!")
            return
        return await handler(message, *args, **kwargs)
    return wrapper


# ==========================================
# 🎛️ MAIN ADMIN MENU
# ==========================================

@enhanced_admin_router.message(Command("admin"), F.from_user.id.in_(ADMIN_ID))
async def admin_main_menu(message: Message):
    """Enhanced admin main menu"""
    # Get quick stats
    sql.execute("SELECT COUNT(*) FROM users_enhanced")
    total_users = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE last_active_at > NOW() - INTERVAL '24 hours'")
    active_today = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM translations_enhanced WHERE DATE(created_at) = CURRENT_DATE")
    translations_today = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM user_feedback WHERE is_resolved = FALSE")
    pending_feedback = sql.fetchone()[0]
    
    text = f"""
👨‍💼 <b>ADMIN PANEL</b>

📊 <b>Tezkor statistika:</b>
├ 👥 Jami foydalanuvchilar: <b>{total_users:,}</b>
├ 🔥 Bugun faol: <b>{active_today:,}</b>
├ 🔄 Bugun tarjima: <b>{translations_today:,}</b>
└ ⚠️ Kutib turgan murojaat: <b>{pending_feedback}</b>

<b>Bo'limni tanlang:</b>
"""
    
    await message.answer(text, reply_markup=admin_kb.main_admin_menu(), parse_mode="HTML")


# ==========================================
# 📈 ADVANCED STATISTICS
# ==========================================

@enhanced_admin_router.message(F.text == "📊 Statistika", F.from_user.id.in_(ADMIN_ID))
async def statistics_menu(message: Message):
    """Statistics menu"""
    await message.answer(
        "📊 <b>STATISTIKA BO'LIMI</b>\n\nBatafsil statistikani ko'rish:",
        reply_markup=admin_kb.statistics_menu(),
        parse_mode="HTML"
    )


@enhanced_admin_router.callback_query(F.data == "stats:overview", F.from_user.id.in_(ADMIN_ID))
async def statistics_overview(callback: CallbackQuery):
    """Comprehensive system overview"""
    # Users stats
    sql.execute("SELECT COUNT(*) FROM users_enhanced")
    total_users = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE created_at > NOW() - INTERVAL '7 days'")
    new_week = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE last_active_at > NOW() - INTERVAL '24 hours'")
    active_24h = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE last_active_at > NOW() - INTERVAL '7 days'")
    active_7d = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE is_premium = TRUE")
    premium_users = sql.fetchone()[0]
    
    # Translation stats
    sql.execute("SELECT COUNT(*) FROM translations_enhanced")
    total_translations = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM translations_enhanced WHERE DATE(created_at) = CURRENT_DATE")
    trans_today = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM translations_enhanced WHERE created_at > NOW() - INTERVAL '7 days'")
    trans_week = sql.fetchone()[0]
    
    # Vocabulary stats
    sql.execute("SELECT COUNT(*) FROM vocab_books_enhanced")
    total_books = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM vocab_entries_enhanced")
    total_words = sql.fetchone()[0]
    
    # Average stats
    sql.execute("SELECT AVG(daily_translation_count) FROM (SELECT COUNT(*) as daily_translation_count FROM translations_enhanced WHERE created_at > NOW() - INTERVAL '30 days' GROUP BY DATE(created_at)) as daily")
    avg_daily_trans = sql.fetchone()[0] or 0
    
    text = f"""
📊 <b>UMUMIY STATISTIKA</b>

👥 <b>Foydalanuvchilar:</b>
├ Jami: <b>{total_users:,}</b>
├ Haftada yangi: <b>+{new_week:,}</b>
├ 24 soatda faol: <b>{active_24h:,}</b>
├ Haftada faol: <b>{active_7d:,}</b>
└ Premium: <b>{premium_users:,}</b> ({premium_users/total_users*100:.1f}%)

🔄 <b>Tarjimalar:</b>
├ Jami: <b>{total_translations:,}</b>
├ Bugun: <b>{trans_today:,}</b>
├ Haftada: <b>{trans_week:,}</b>
└ O'rtacha kunlik: <b>{avg_daily_trans:.0f}</b>

📚 <b>Lug'atlar:</b>
├ Jami kitoblar: <b>{total_books:,}</b>
└ Jami so'zlar: <b>{total_words:,}</b>

🕐 <i>Yangilangan: {datetime.now().strftime('%H:%M:%S')}</i>
"""
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=FancyButtons.REFRESH, callback_data="stats:overview")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="stats:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "stats:growth", F.from_user.id.in_(ADMIN_ID))
async def growth_analytics(callback: CallbackQuery):
    """User growth analytics"""
    # Daily growth for last 14 days
    sql.execute("""
        SELECT DATE(created_at) as date, COUNT(*) as count
        FROM users_enhanced
        WHERE created_at > NOW() - INTERVAL '14 days'
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        LIMIT 14
    """)
    
    growth_data = sql.fetchall()
    
    text = "📈 <b>O'SISH DINAMIKASI</b> (Oxirgi 14 kun)\n\n"
    text += "<code>Kun         | Yangi | Jami</code>\n"
    text += "<code>────────────┼───────┼─────────</code>\n"
    
    cumulative = 0
    for date_val, count in reversed(growth_data):
        cumulative += count
        date_str = date_val.strftime("%d.%m")
        text += f"<code>{date_str}      | {count:5d} | {cumulative:7d}</code>\n"
    
    # Growth rate
    if len(growth_data) >= 7:
        recent = sum(c for _, c in growth_data[:7])
        previous = sum(c for _, c in growth_data[7:14]) if len(growth_data) >= 14 else recent
        growth_rate = ((recent - previous) / previous * 100) if previous > 0 else 0
        
        trend = "📈" if growth_rate > 0 else "📉" if growth_rate < 0 else "➡️"
        text += f"\n{trend} <b>O'sish sur'ati:</b> {growth_rate:+.1f}%"
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Batafsil grafik", callback_data="stats:graph")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="stats:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "stats:languages", F.from_user.id.in_(ADMIN_ID))
async def language_stats(callback: CallbackQuery):
    """Language usage statistics"""
    sql.execute("""
        SELECT from_lang, to_lang, COUNT(*) as count
        FROM translations_enhanced
        GROUP BY from_lang, to_lang
        ORDER BY count DESC
        LIMIT 15
    """)
    
    pairs = sql.fetchall()
    
    text = "🌍 <b>TILLAR BO'YICHA STATISTIKA</b>\n\n"
    text += "<b>Top til juftliklari:</b>\n"
    
    for i, (from_lang, to_lang, count) in enumerate(pairs, 1):
        flag_from = "🌐" if from_lang == 'auto' else get_flag(from_lang)
        flag_to = get_flag(to_lang)
        text += f"{i:2d}. {flag_from} → {flag_to} <b>{count:,}</b>\n"
    
    # Most popular target languages
    sql.execute("""
        SELECT to_lang, COUNT(*) as count
        FROM translations_enhanced
        GROUP BY to_lang
        ORDER BY count DESC
        LIMIT 5
    """)
    
    targets = sql.fetchall()
    text += "\n<b>Mashhur maqsad tillari:</b>\n"
    for lang, count in targets:
        text += f"  {get_flag(lang)} {count:,}\n"
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="stats:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "stats:export", F.from_user.id.in_(ADMIN_ID))
async def export_statistics(callback: CallbackQuery):
    """Export statistics to CSV"""
    # Generate CSV data
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(['Metric', 'Value', 'Date'])
    
    # User stats
    sql.execute("SELECT COUNT(*) FROM users_enhanced")
    writer.writerow(['Total Users', sql.fetchone()[0], date.today()])
    
    sql.execute("SELECT COUNT(*) FROM translations_enhanced")
    writer.writerow(['Total Translations', sql.fetchone()[0], date.today()])
    
    # Daily stats for last 30 days
    sql.execute("""
        SELECT DATE(created_at) as date, COUNT(*) 
        FROM translations_enhanced 
        WHERE created_at > NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    
    for date_val, count in sql.fetchall():
        writer.writerow(['Daily Translations', count, date_val])
    
    # Send file
    csv_data = output.getvalue().encode('utf-8')
    file = BufferedInputFile(csv_data, filename=f"stats_{date.today()}.csv")
    
    await callback.message.answer_document(
        file,
        caption=f"📊 Statistika hisoboti ({date.today()})"
    )
    await callback.answer("✅ Yuklandi!")


def get_flag(lang_code: str) -> str:
    """Get flag emoji for language code"""
    flags = {
        'en': '🇬🇧', 'uz': '🇺🇿', 'ru': '🇷🇺', 'tr': '🇹🇷', 'ar': '🇸🇦',
        'de': '🇩🇪', 'fr': '🇫🇷', 'es': '🇪🇸', 'it': '🇮🇹', 'pt': '🇵🇹',
        'zh': '🇨🇳', 'ja': '🇯🇵', 'ko': '🇰🇷', 'hi': '🇮🇳', 'id': '🇮🇩',
        'fa': '🇮🇷', 'kk': '🇰🇿', 'ky': '🇰🇬', 'az': '🇦🇿', 'tk': '🇹🇲',
        'tg': '🇹🇯', 'pl': '🇵🇱', 'am': '🇪🇹', 'nl': '🇳🇱', 'auto': '🌐',
    }
    return flags.get(lang_code, '🏳️')


# ==========================================
# 👥 USER MANAGEMENT
# ==========================================

@enhanced_admin_router.message(F.text == "👥 Foydalanuvchilar", F.from_user.id.in_(ADMIN_ID))
async def user_management_menu(message: Message):
    """User management menu"""
    await message.answer(
        "👥 <b>FOYDALANUVCHILAR BOSHQARUVI</b>",
        reply_markup=admin_kb.user_management_menu(),
        parse_mode="HTML"
    )


@enhanced_admin_router.callback_query(F.data == "users:list", F.from_user.id.in_(ADMIN_ID))
async def list_users(callback: CallbackQuery):
    """Show user list with pagination"""
    sql.execute("""
        SELECT user_id, first_name, username, created_at, last_active_at, is_blocked
        FROM users_enhanced
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    users = sql.fetchall()
    
    text = "📋 <b>OXIRGI FOYDALANUVCHILAR</b>\n\n"
    
    for user in users:
        user_id, name, username, created, last_active, blocked = user
        status = "🚫" if blocked else "✅"
        name_short = (name[:20] + "...") if name and len(name) > 20 else (name or "N/A")
        
        text += (
            f"{status} <code>{user_id}</code>\n"
            f"   👤 {name_short}\n"
            f"   📅 {created.strftime('%d.%m.%Y')}\n\n"
        )
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Qidirish", callback_data="users:search")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="users:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "users:search", F.from_user.id.in_(ADMIN_ID))
async def search_user_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user search"""
    await state.set_state(AdminStates.user_search)
    await callback.message.answer(
        "🔍 <b>Foydalanuvchini qidirish</b>\n\n"
        "ID, username yoki ism yuboring:"
    )
    await callback.answer()


@enhanced_admin_router.message(AdminStates.user_search, F.from_user.id.in_(ADMIN_ID))
async def search_user(message: Message, state: FSMContext):
    """Search for user"""
    query = message.text.strip()
    
    # Try to search by different criteria
    try:
        user_id = int(query)
        sql.execute("""
            SELECT user_id, first_name, username, created_at, last_active_at, 
                   is_blocked, is_premium, streak_days, user_level
            FROM users_enhanced WHERE user_id = %s
        """, (user_id,))
    except ValueError:
        # Search by username or name
        sql.execute("""
            SELECT user_id, first_name, username, created_at, last_active_at,
                   is_blocked, is_premium, streak_days, user_level
            FROM users_enhanced 
            WHERE username ILIKE %s OR first_name ILIKE %s
            LIMIT 5
        """, (f"%{query}%", f"%{query}%"))
    
    results = sql.fetchall()
    
    if not results:
        await message.answer("❌ Foydalanuvchi topilmadi")
    else:
        for user in results:
            user_id, name, username, created, last_active, blocked, premium, streak, level = user
            
            status_badges = []
            if blocked:
                status_badges.append("🚫 BLOKLAGAN")
            if premium:
                status_badges.append("💎 PREMIUM")
            
            text = f"""
👤 <b>Foydalanuvchi ma'lumotlari</b>

🆔 <b>ID:</b> <code>{user_id}</code>
👤 <b>Ism:</b> {name or 'N/A'}
📱 <b>Username:</b> {'@' + username if username else 'N/A'}
📅 <b>Ro'yxatdan o'tgan:</b> {created.strftime('%d.%m.%Y %H:%M')}
🕐 <b>So'nggi faollik:</b> {last_active.strftime('%d.%m.%Y %H:%M') if last_active else 'N/A'}
⭐ <b>Level:</b> {level}
🔥 <b>Izchillik:</b> {streak} kun
{" | ".join(status_badges) if status_badges else ''}
"""
            
            # Action buttons
            builder = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✉️ Xabar yuborish", 
                        callback_data=f"admin:msg:{user_id}"
                    ),
                    InlineKeyboardButton(
                        text="🚫 Bloklash" if not blocked else "✅ Blokdan chiqarish",
                        callback_data=f"admin:block:{user_id}:{int(not blocked)}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="💎 Premium berish" if not premium else "❌ Premium olib tashlash",
                        callback_data=f"admin:premium:{user_id}:{int(not premium)}"
                    )
                ]
            ])
            
            await message.answer(text, reply_markup=builder, parse_mode="HTML")
    
    await state.clear()


# ==========================================
# 📢 BROADCAST SYSTEM
# ==========================================

@enhanced_admin_router.message(F.text == "📢 Xabar yuborish", F.from_user.id.in_(ADMIN_ID))
async def broadcast_menu(message: Message):
    """Broadcast menu"""
    await message.answer(
        "📢 <b>XABAR YUBORISH</b>",
        reply_markup=admin_kb.broadcast_menu(),
        parse_mode="HTML"
    )


@enhanced_admin_router.callback_query(F.data == "broadcast:copy", F.from_user.id.in_(ADMIN_ID))
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast process"""
    await state.set_state(AdminStates.broadcast_message)
    await callback.message.answer(
        "📢 <b>XABAR YUBORISH</b>\n\n"
        "Yuboriladigan xabarni yuboring:\n\n"
        "📝 Matn, rasm, video yoki boshqa media"
    )
    await callback.answer()


@enhanced_admin_router.message(AdminStates.broadcast_message, F.from_user.id.in_(ADMIN_ID))
async def confirm_broadcast(message: Message, state: FSMContext):
    """Confirm and send broadcast"""
    # Store message for broadcasting
    await state.update_data(broadcast_message=message)
    
    # Get user count
    sql.execute("SELECT COUNT(*) FROM users_enhanced WHERE is_blocked = FALSE")
    user_count = sql.fetchone()[0]
    
    text = f"""
📢 <b>XABAR YUBORISH TASDIG'I</b>

👥 <b>Qabulchilar:</b> {user_count:,} ta foydalanuvchi
⚠️ <b>Diqqat:</b> Bu jarayon bir necha daqiqa davom etishi mumkin!

Xabarni yuborishni tasdiqlaysizmi?
"""
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="broadcast:confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast:cancel")
        ]
    ])
    
    await message.answer(text, reply_markup=builder, parse_mode="HTML")


@enhanced_admin_router.callback_query(F.data == "broadcast:confirm", F.from_user.id.in_(ADMIN_ID))
async def execute_broadcast(callback: CallbackQuery, state: FSMContext):
    """Execute the broadcast"""
    data = await state.get_data()
    message_to_send = data.get('broadcast_message')
    
    if not message_to_send:
        await callback.answer("❌ Xabar topilmadi!")
        return
    
    # Get all users
    sql.execute("SELECT user_id FROM users_enhanced WHERE is_blocked = FALSE")
    users = [row[0] for row in sql.fetchall()]
    
    status_message = await callback.message.answer(
        f"📤 Yuborish boshlandi...\n👥 Jami: {len(users)}"
    )
    
    success = 0
    failed = 0
    
    for i, user_id in enumerate(users):
        try:
            await message_to_send.copy_to(user_id)
            success += 1
        except Exception as e:
            failed += 1
            print(f"Failed to send to {user_id}: {e}")
        
        # Update status every 50 users
        if i % 50 == 0:
            try:
                await status_message.edit_text(
                    f"📤 Yuborilmoqda...\n"
                    f"✅ {success} | ❌ {failed}\n"
                    f"📊 {i+1}/{len(users)}"
                )
            except:
                pass
        
        await asyncio.sleep(0.05)  # Rate limiting
    
    await status_message.edit_text(
        f"✅ <b>YUBORISH TUGADI</b>\n\n"
        f"✅ Muvaffaqiyatli: {success}\n"
        f"❌ Muvaffaqiyatsiz: {failed}\n"
        f"📊 Jami: {len(users)}"
    )
    
    await state.clear()
    await callback.answer()


# ==========================================
# 🎮 GAMIFICATION ADMIN
# ==========================================

@enhanced_admin_router.message(F.text == "🎮 Gamification", F.from_user.id.in_(ADMIN_ID))
async def gamification_menu(message: Message):
    """Gamification management menu"""
    await message.answer(
        "🎮 <b>GAMIFICATION BOSHQARUVI</b>",
        reply_markup=admin_kb.gamification_admin(),
        parse_mode="HTML"
    )


@enhanced_admin_router.callback_query(F.data == "game:achievements", F.from_user.id.in_(ADMIN_ID))
async def manage_achievements(callback: CallbackQuery):
    """Manage achievements"""
    sql.execute("SELECT COUNT(*) FROM achievements")
    total_ach = sql.fetchone()[0]
    
    sql.execute("SELECT COUNT(*) FROM user_achievements")
    unlocked_ach = sql.fetchone()[0]
    
    text = f"""
🏆 <b>YUTUQLAR BOSHQARUVI</b>

📊 <b>Statistika:</b>
├ Jami yutuqlar: <b>{total_ach}</b>
└ Ochilgan yutuqlar: <b>{unlocked_ach}</b>

<b>Amallar:</b>
"""
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi yutuq", callback_data="ach:create")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="ach:list")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="game:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "game:daily", F.from_user.id.in_(ADMIN_ID))
async def manage_daily_challenges(callback: CallbackQuery):
    """Manage daily challenges"""
    # Get today's challenge
    sql.execute("""
        SELECT title, description, target_value, reward_xp,
               (SELECT COUNT(*) FROM user_daily_challenges WHERE challenge_id = dc.id) as participants,
               (SELECT COUNT(*) FROM user_daily_challenges WHERE challenge_id = dc.id AND is_completed = TRUE) as completed
        FROM daily_challenges dc
        WHERE date = CURRENT_DATE
    """)
    
    challenge = sql.fetchone()
    
    if challenge:
        title, desc, target, reward, participants, completed = challenge
        completion_rate = (completed / participants * 100) if participants > 0 else 0
        
        text = f"""
🎯 <b>KUNLIK VAZIFA — BUGUN</b>

<b>{title}</b>
{desc}

📊 <b>Statistika:</b>
├ Ishtirokchilar: <b>{participants}</b>
├ Bajardi: <b>{completed}</b>
└ Bajarish darajasi: <b>{completion_rate:.1f}%</b>

🎁 Mukofot: <b>{reward} XP</b>
"""
    else:
        text = "⚠️ <b>Bugun uchun vazifa yaratilmagan!</b>"
    
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi vazifa", callback_data="daily:create")],
        [InlineKeyboardButton(text=FancyButtons.BACK, callback_data="game:back")]
    ])
    
    await callback.message.edit_text(text, reply_markup=builder, parse_mode="HTML")
    await callback.answer()


# ==========================================
# 🔙 BACK HANDLERS
# ==========================================

@enhanced_admin_router.callback_query(F.data.endswith(":back"), F.from_user.id.in_(ADMIN_ID))
async def back_handler(callback: CallbackQuery):
    """Generic back handler"""
    await callback.message.delete()
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "stats:back", F.from_user.id.in_(ADMIN_ID))
async def back_to_stats_menu(callback: CallbackQuery):
    """Back to statistics menu"""
    await statistics_menu(callback.message)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "users:back", F.from_user.id.in_(ADMIN_ID))
async def back_to_users_menu(callback: CallbackQuery):
    """Back to users menu"""
    await user_management_menu(callback.message)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()


@enhanced_admin_router.callback_query(F.data == "broadcast:cancel", F.from_user.id.in_(ADMIN_ID))
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await state.clear()
    await callback.message.edit_text("❌ Xabar yuborish bekor qilindi.")
    await callback.answer()


@enhanced_admin_router.message(F.text == "🔙 Chiqish", F.from_user.id.in_(ADMIN_ID))
async def exit_admin(message: Message):
    """Exit admin panel"""
    from src.keyboards.buttons import UserPanels
    await message.answer(
        "👋 Admin paneldan chiqdingiz.",
        reply_markup=await UserPanels.user_main_menu()
    )
