"""
👨‍💼 Complete Admin Panel for Tarjimon Bot
Fully functional admin handlers
"""

import asyncio
import io
import csv
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from config import sql, db, bot, ADMIN_ID, DB_CONFIG

admin_complete_router = Router()


# ==========================================
# 📊 STATES
# ==========================================

class AdminStates(StatesGroup):
    # Broadcast states
    broadcast_simple = State()      # Waiting for simple message
    broadcast_forward = State()     # Waiting for forward message
    broadcast_confirm = State()     # Waiting for confirmation (yes/no)
    # Other states
    user_search = State()
    channel_add = State()
    channel_link = State()


# ==========================================
# 🔧 HELPER FUNCTIONS
# ==========================================

def get_admin_main_menu() -> ReplyKeyboardMarkup:
    """Admin main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="👥 Foydalanuvchilar")],
            [KeyboardButton(text="📢 Xabar yuborish"), KeyboardButton(text="🔧 Kanallar")],
            [KeyboardButton(text="🎮 Gamification"), KeyboardButton(text="🔙 Chiqish")],
        ],
        resize_keyboard=True
    )


def get_stats_menu() -> InlineKeyboardMarkup:
    """Statistics inline menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Umumiy", callback_data="admin:stats:overview"),
            InlineKeyboardButton(text="📈 O'sish", callback_data="admin:stats:growth")
        ],
        [
            InlineKeyboardButton(text="🌍 Tillar", callback_data="admin:stats:languages"),
            InlineKeyboardButton(text="📥 Export", callback_data="admin:stats:export")
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])


def get_users_menu() -> InlineKeyboardMarkup:
    """User management inline menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin:users:search")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin:users:list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])


def get_broadcast_menu() -> InlineKeyboardMarkup:
    """Broadcast inline menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📨 Forward xabar", callback_data="admin:broadcast:forward")],
        [InlineKeyboardButton(text="📬 Oddiy xabar (Copy)", callback_data="admin:broadcast:simple")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])


def get_broadcast_confirm_menu(msg_type: str) -> InlineKeyboardMarkup:
    """Broadcast confirmation menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, yuborish", callback_data=f"admin:broadcast:confirm:yes:{msg_type}"),
            InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="admin:broadcast:confirm:no")
        ]
    ])


def get_channels_menu() -> InlineKeyboardMarkup:
    """Channels inline menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="admin:channel:add")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admin:channel:list")],
        [InlineKeyboardButton(text="❌ O'chirish", callback_data="admin:channel:delete")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])


def get_gamification_menu() -> InlineKeyboardMarkup:
    """Gamification inline menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Yutuqlar", callback_data="admin:game:achievements")],
        [InlineKeyboardButton(text="🎯 Kunlik vazifa", callback_data="admin:game:daily")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])


def get_flag(lang_code: str) -> str:
    """Get flag emoji for language"""
    flags = {
        'en': '🇬🇧', 'uz': '🇺🇿', 'ru': '🇷🇺', 'tr': '🇹🇷', 'ar': '🇸🇦',
        'de': '🇩🇪', 'fr': '🇫🇷', 'es': '🇪🇸', 'it': '🇮🇹', 'pt': '🇵🇹',
        'zh': '🇨🇳', 'ja': '🇯🇵', 'ko': '🇰🇷', 'hi': '🇮🇳', 'id': '🇮🇩',
        'fa': '🇮🇷', 'kk': '🇰🇿', 'ky': '🇰🇬', 'az': '🇦🇿', 'tk': '🇹🇲',
        'auto': '🌐'
    }
    return flags.get(lang_code, '🏳️')


# ==========================================
# 🎛️ MAIN ADMIN ENTRY
# ==========================================

@admin_complete_router.message(Command("admin"), F.from_user.id.in_(ADMIN_ID))
async def cmd_admin(message: Message):
    """Main admin command"""
    # Get basic stats
    try:
        sql.execute("SELECT COUNT(*) FROM users")
        total_users = sql.fetchone()[0]
    except:
        total_users = 0
    
    text = f"""
👨‍💼 <b>ADMIN PANEL</b>

📊 <b>Tezkor statistika:</b>
├ 👥 Jami foydalanuvchilar: <b>{total_users}</b>
└ 🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}

<b>Bo'limni tanlang:</b>
"""
    await message.answer(text, reply_markup=get_admin_main_menu(), parse_mode="HTML")


# ==========================================
# 📊 STATISTICS SECTION
# ==========================================

@admin_complete_router.message(F.text == "📊 Statistika", F.from_user.id.in_(ADMIN_ID))
async def stats_menu(message: Message):
    """Show statistics menu"""
    await message.answer(
        "📊 <b>STATISTIKA BO'LIMI</b>\n\nBatafsil ma'lumot olish:",
        reply_markup=get_stats_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(F.data == "admin:stats:overview", F.from_user.id.in_(ADMIN_ID))
async def stats_overview(callback: CallbackQuery):
    """Show comprehensive overview statistics"""
    try:
        # Users
        sql.execute("SELECT COUNT(*) FROM users")
        total_users = sql.fetchone()[0]
        
        sql.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
        today_users = sql.fetchone()[0]
        
        sql.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        week_users = sql.fetchone()[0]
        
        sql.execute("""
            SELECT COUNT(*) FROM users 
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        month_users = sql.fetchone()[0]
        
        # Active users (have translations)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) FROM translation_history 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        active_week = sql.fetchone()[0] or 0
        
        # Translations
        sql.execute("SELECT COUNT(*) FROM translation_history")
        result = sql.fetchone()
        total_trans = result[0] if result else 0
        
        sql.execute("SELECT COUNT(*) FROM translation_history WHERE DATE(created_at) = CURRENT_DATE")
        result = sql.fetchone()
        today_trans = result[0] if result else 0
        
        sql.execute("""
            SELECT COUNT(*) FROM translation_history 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        week_trans = sql.fetchone()[0] or 0
        
        # Vocabulary
        sql.execute("SELECT COUNT(*) FROM vocab_books")
        total_books = sql.fetchone()[0] or 0
        
        sql.execute("SELECT COUNT(*) FROM vocab_entries")
        total_entries = sql.fetchone()[0] or 0
        
        # Average translations per user
        avg_trans = round(total_trans / total_users, 2) if total_users > 0 else 0
        
        text = f"""
📊 <b>UMUMIY STATISTIKA</b>

👥 <b>Foydalanuvchilar:</b>
├ Jami: <b>{total_users:,}</b>
├ Bugun: <b>+{today_users}</b>
├ Haftada: <b>+{week_users}</b>
├ 30 kun: <b>+{month_users}</b>
└ Faol (7 kun): <b>{active_week}</b>

🔄 <b>Tarjimalar:</b>
├ Jami: <b>{total_trans:,}</b>
├ Bugun: <b>{today_trans}</b>
├ Haftada: <b>{week_trans}</b>
└ Foydalanuvchi boshiga: <b>{avg_trans}</b>

📚 <b>Lug'atlar:</b>
├ Jami kitoblar: <b>{total_books:,}</b>
└ Jami so'zlar: <b>{total_entries:,}</b>

🕐 <i>{datetime.now().strftime('%H:%M:%S')}</i>
"""
    except Exception as e:
        text = f"❌ Xatolik: {str(e)}"
    
    await callback.message.edit_text(text, reply_markup=get_stats_menu(), parse_mode="HTML")
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:stats:growth", F.from_user.id.in_(ADMIN_ID))
async def stats_growth(callback: CallbackQuery):
    """Show detailed growth statistics"""
    try:
        # User growth last 14 days
        sql.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users 
            WHERE created_at > NOW() - INTERVAL '14 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        user_data = sql.fetchall()
        
        # Translation growth last 14 days
        sql.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as new_trans
            FROM translation_history 
            WHERE created_at > NOW() - INTERVAL '14 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)
        trans_data = sql.fetchall()
        
        text = "📈 <b>O'SISH DINAMIKASI</b> (Oxirgi 14 kun)\n\n"
        
        # Create a combined view
        all_dates = set()
        user_dict = {}
        trans_dict = {}
        
        for date_val, count in user_data:
            all_dates.add(date_val)
            user_dict[date_val] = count
            
        for date_val, count in trans_data:
            all_dates.add(date_val)
            trans_dict[date_val] = count
        
        # Sort dates and build text
        sorted_dates = sorted(all_dates, reverse=True)
        
        text += "📅 <b>Sana</b>      👥 <b>Foyd.</b>   🔄 <b>Tarj.</b>\n"
        text += "─" * 35 + "\n"
        
        for dt in sorted_dates[:14]:  # Last 14 days
            date_str = dt.strftime('%d.%m')
            users = user_dict.get(dt, 0)
            trans = trans_dict.get(dt, 0)
            
            # Add trend indicators
            user_trend = "📈" if users > 10 else "📊" if users > 0 else "➖"
            
            text += f"{date_str:12} +{users:4}     {trans:4} {user_trend}\n"
        
        # Summary
        total_new_users = sum(user_dict.values())
        total_new_trans = sum(trans_dict.values())
        
        text += f"\n📊 <b>Jami:</b> +{total_new_users} foydalanuvchi, {total_new_trans:,} tarjima\n"
        
        # Average daily growth
        avg_daily = round(total_new_users / len(sorted_dates), 1) if sorted_dates else 0
        text += f"📉 <b>O'rtacha kunlik:</b> +{avg_daily} foydalanuvchi"
        
    except Exception as e:
        text = f"❌ Xatolik: {str(e)}"
    
    await callback.message.edit_text(text, reply_markup=get_stats_menu(), parse_mode="HTML")
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:stats:languages", F.from_user.id.in_(ADMIN_ID))
async def stats_languages(callback: CallbackQuery):
    """Show comprehensive language statistics"""
    try:
        # Top target languages
        sql.execute("""
            SELECT 
                COALESCE(to_lang, 'unknown') as lang,
                COUNT(*) as count
            FROM translation_history
            GROUP BY to_lang
            ORDER BY count DESC
            LIMIT 10
        """)
        target_langs = sql.fetchall()
        
        # User language preferences
        sql.execute("""
            SELECT 
                COALESCE(interface_lang, 'uz') as lang,
                COUNT(*) as count
            FROM users
            GROUP BY interface_lang
            ORDER BY count DESC
            LIMIT 5
        """)
        user_langs = sql.fetchall()
        
        # Total count for percentage calculation
        sql.execute("SELECT COUNT(*) FROM translation_history")
        total_count = sql.fetchone()[0] or 1
        
        text = "🌍 <b>TIL STATISTIKASI</b>\n\n"
        
        # Target languages (what users translate TO)
        text += "🎯 <b>Tarjima tillari (TOP 10):</b>\n"
        for i, (lang, count) in enumerate(target_langs, 1):
            flag = get_flag(lang)
            percentage = round((count / total_count) * 100, 1)
            bar = "█" * int(percentage / 5) + "░" * (20 - int(percentage / 5))
            text += f"{i:2}. {flag} <b>{lang.upper():6}</b> {bar} {count:,} ({percentage}%)\n"
        
        # User interface languages
        text += "\n👤 <b>Foydalanuvchi tillari:</b>\n"
        for lang, count in user_langs:
            flag = get_flag(lang)
            text += f"   {flag} <b>{lang.upper()}</b>: {count:,} ta\n"
        
    except Exception as e:
        text = f"❌ Xatolik: {str(e)}"
    
    await callback.message.edit_text(text, reply_markup=get_stats_menu(), parse_mode="HTML")
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:stats:export", F.from_user.id.in_(ADMIN_ID))
async def stats_export(callback: CallbackQuery):
    """Export comprehensive statistics to CSV with all user data"""
    import tempfile
    import zipfile
    
    status_msg = await callback.message.answer("📊 Ma'lumotlar yig'ilmoqda...")
    
    try:
        # Create temp directory for files
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, f"tarjimon_stats_{date.today()}.zip")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # ========== FILE 1: USERS_DATA.csv - ALL USER DATA WITH IDs ==========
                users_output = io.StringIO()
                users_writer = csv.writer(users_output)
                
                # Headers with all user fields
                users_writer.writerow([
                    'ID', 'Telegram ID', 'First Name', 'Username', 'Language Code',
                    'Created At', 'Updated At', 'Is Blocked', 'Translations Count'
                ])
                
                # Get all users with their translation counts
                sql.execute("""
                    SELECT 
                        a.id,
                        a.user_id,
                        a.first_name,
                        a.username,
                        a.interface_lang,
                        a.created_at,
                        a.updated_at,
                        a.is_blocked,
                        COALESCE(t.translation_count, 0) as translations
                    FROM users a
                    LEFT JOIN (
                        SELECT user_id, COUNT(*) as translation_count 
                        FROM translation_history 
                        GROUP BY user_id
                    ) t ON a.user_id = t.user_id
                    ORDER BY a.created_at DESC
                """)
                
                users = sql.fetchall()
                for user in users:
                    users_writer.writerow([
                        user[0],           # ID
                        user[1],           # Telegram ID
                        user[2] or '',     # First Name
                        user[3] or '',     # Username
                        user[4] or 'uz',   # Language Code
                        user[5].strftime('%Y-%m-%d %H:%M:%S') if user[5] else '',  # Created At
                        user[6].strftime('%Y-%m-%d %H:%M:%S') if user[6] else '',  # Updated At
                        'Yes' if user[7] else 'No',  # Is Blocked
                        user[8]            # Translations Count
                    ])
                
                users_csv = users_output.getvalue().encode('utf-8')
                zipf.writestr("01_USERS_DATA.csv", users_csv)
                total_users = len(users)
                
                # ========== FILE 2: SUMMARY_STATISTICS.csv ==========
                summary_output = io.StringIO()
                summary_writer = csv.writer(summary_output)
                summary_writer.writerow(['Metric', 'Value', 'Date'])
                
                # Total users
                summary_writer.writerow(['Total Users', total_users, date.today()])
                
                # Today's new users
                sql.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
                today_users = sql.fetchone()[0]
                summary_writer.writerow(['New Users Today', today_users, date.today()])
                
                # Users this week
                sql.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at > NOW() - INTERVAL '7 days'
                """)
                week_users = sql.fetchone()[0]
                summary_writer.writerow(['New Users This Week', week_users, date.today()])
                
                # Users this month
                sql.execute("""
                    SELECT COUNT(*) FROM users 
                    WHERE created_at > NOW() - INTERVAL '30 days'
                """)
                month_users = sql.fetchone()[0]
                summary_writer.writerow(['New Users This Month', month_users, date.today()])
                
                # Total translations
                sql.execute("SELECT COUNT(*) FROM translation_history")
                total_trans = sql.fetchone()[0] or 0
                summary_writer.writerow(['Total Translations', total_trans, date.today()])
                
                # Today's translations
                sql.execute("""
                    SELECT COUNT(*) FROM translation_history 
                    WHERE DATE(created_at) = CURRENT_DATE
                """)
                today_trans = sql.fetchone()[0] or 0
                summary_writer.writerow(['Translations Today', today_trans, date.today()])
                
                # Total vocab books
                sql.execute("SELECT COUNT(*) FROM vocab_books")
                total_books = sql.fetchone()[0] or 0
                summary_writer.writerow(['Total Vocab Books', total_books, date.today()])
                
                # Total vocab entries
                sql.execute("SELECT COUNT(*) FROM vocab_entries")
                total_entries = sql.fetchone()[0] or 0
                summary_writer.writerow(['Total Vocab Entries', total_entries, date.today()])
                
                summary_csv = summary_output.getvalue().encode('utf-8')
                zipf.writestr("02_SUMMARY_STATISTICS.csv", summary_csv)
                
                # ========== FILE 3: DAILY_GROWTH.csv ==========
                growth_output = io.StringIO()
                growth_writer = csv.writer(growth_output)
                growth_writer.writerow(['Date', 'New Users', 'New Translations', 'Cumulative Users'])
                
                sql.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as new_users
                    FROM users 
                    WHERE created_at > NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """)
                daily_users = {row[0]: row[1] for row in sql.fetchall()}
                
                sql.execute("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as new_trans
                    FROM translation_history 
                    WHERE created_at > NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """)
                daily_trans = {row[0]: row[1] for row in sql.fetchall()}
                
                # Get all dates from both datasets
                all_dates = set(daily_users.keys()) | set(daily_trans.keys())
                
                running_total = total_users - sum(daily_users.values())
                for dt in sorted(all_dates, reverse=True):
                    new_users = daily_users.get(dt, 0)
                    running_total += new_users
                    growth_writer.writerow([
                        dt.strftime('%Y-%m-%d'),
                        new_users,
                        daily_trans.get(dt, 0),
                        running_total
                    ])
                
                growth_csv = growth_output.getvalue().encode('utf-8')
                zipf.writestr("03_DAILY_GROWTH.csv", growth_csv)
                
                # ========== FILE 4: LANGUAGE_STATISTICS.csv ==========
                lang_output = io.StringIO()
                lang_writer = csv.writer(lang_output)
                lang_writer.writerow(['Language Code', 'Translation Count', 'Percentage'])
                
                sql.execute("""
                    SELECT 
                        COALESCE(to_lang, 'unknown') as lang,
                        COUNT(*) as count
                    FROM translation_history 
                    GROUP BY to_lang
                    ORDER BY count DESC
                """)
                
                lang_data = sql.fetchall()
                total_lang_count = sum(row[1] for row in lang_data) or 1
                
                for lang, count in lang_data:
                    percentage = round((count / total_lang_count) * 100, 2)
                    lang_writer.writerow([lang, count, f"{percentage}%"])
                
                lang_csv = lang_output.getvalue().encode('utf-8')
                zipf.writestr("04_LANGUAGE_STATISTICS.csv", lang_csv)
                
                # ========== FILE 5: TOP_ACTIVE_USERS.csv ==========
                top_output = io.StringIO()
                top_writer = csv.writer(top_output)
                top_writer.writerow(['Rank', 'User ID', 'First Name', 'Username', 'Translations Count'])
                
                sql.execute("""
                    SELECT 
                        th.user_id,
                        a.first_name,
                        a.username,
                        COUNT(*) as trans_count
                    FROM translation_history th
                    JOIN users a ON th.user_id = a.user_id
                    GROUP BY th.user_id, a.first_name, a.username
                    ORDER BY trans_count DESC
                    LIMIT 100
                """)
                
                top_users = sql.fetchall()
                for rank, user in enumerate(top_users, 1):
                    top_writer.writerow([
                        rank,
                        user[0],
                        user[1] or '',
                        user[2] or '',
                        user[3]
                    ])
                
                top_csv = top_output.getvalue().encode('utf-8')
                zipf.writestr("05_TOP_ACTIVE_USERS.csv", top_csv)
            
            # Delete status message
            await status_msg.delete()
            
            # Send the zip file
            with open(zip_path, 'rb') as f:
                zip_data = f.read()
                file = BufferedInputFile(zip_data, filename=f"tarjimon_stats_{date.today()}.zip")
                
                await callback.message.answer_document(
                    file,
                    caption=(
                        f"📊 <b>TO'LIQ STATISTIKA</b>\n\n"
                        f"📁 Fayllar ro'yxati:\n"
                        f"1️⃣ <b>USERS_DATA.csv</b> - Barcha foydalanuvchilar ({total_users} ta)\n"
                        f"2️⃣ <b>SUMMARY_STATISTICS.csv</b> - Umumiy statistika\n"
                        f"3️⃣ <b>DAILY_GROWTH.csv</b> - Kunlik o'sish (30 kun)\n"
                        f"4️⃣ <b>LANGUAGE_STATISTICS.csv</b> - Til statistikasi\n"
                        f"5️⃣ <b>TOP_ACTIVE_USERS.csv</b> - Eng faol 100 foydalanuvchi\n\n"
                        f"📅 Sana: {date.today()}"
                    ),
                    parse_mode="HTML"
                )
            
            await callback.answer("✅ Yuklandi!")
            
    except Exception as e:
        await status_msg.delete()
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)
        import traceback
        traceback.print_exc()


# ==========================================
# 👥 USERS SECTION
# ==========================================

@admin_complete_router.message(F.text == "👥 Foydalanuvchilar", F.from_user.id.in_(ADMIN_ID))
async def users_menu(message: Message):
    """Show users menu"""
    await message.answer(
        "👥 <b>FOYDALANUVCHILAR</b>",
        reply_markup=get_users_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(F.data == "admin:users:list", F.from_user.id.in_(ADMIN_ID))
async def users_list(callback: CallbackQuery):
    """List recent users"""
    try:
        sql.execute("""
            SELECT user_id, first_name, username, created_at 
            FROM users 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        users = sql.fetchall()
        
        text = "📋 <b>OXIRGI FOYDALANUVCHILAR</b>\n\n"
        for user_id, name, username, created in users:
            name_short = (name[:15] + "...") if name and len(name) > 15 else (name or "N/A")
            date_str = created.strftime('%d.%m.%Y') if created else "N/A"
            text += f"👤 <code>{user_id}</code> - {name_short}\n📅 {date_str}\n\n"
    except Exception as e:
        text = f"❌ Xatolik: {str(e)}"
    
    await callback.message.edit_text(text, reply_markup=get_users_menu(), parse_mode="HTML")
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:users:search", F.from_user.id.in_(ADMIN_ID))
async def users_search_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for user search"""
    await state.set_state(AdminStates.user_search)
    await callback.message.answer("🔍 ID yoki username yuboring:")
    await callback.answer()


@admin_complete_router.message(AdminStates.user_search, F.from_user.id.in_(ADMIN_ID))
async def users_search_execute(message: Message, state: FSMContext):
    """Execute user search"""
    query = message.text.strip()
    
    try:
        # Try as ID first
        try:
            user_id = int(query)
            sql.execute("SELECT user_id, first_name, username, created_at FROM users WHERE user_id = %s", (user_id,))
        except ValueError:
            # Search by username
            sql.execute("""
                SELECT user_id, first_name, username, created_at 
                FROM users 
                WHERE username ILIKE %s
                LIMIT 5
            """, (f"%{query}%",))
        
        results = sql.fetchall()
        
        if not results:
            await message.answer("❌ Foydalanuvchi topilmadi")
        else:
            for user_id, name, username, created in results:
                date_str = created.strftime('%d.%m.%Y %H:%M') if created else "N/A"
                text = f"""
👤 <b>Foydalanuvchi</b>
🆔 ID: <code>{user_id}</code>
👤 Ism: {name or 'N/A'}
📱 Username: {'@' + username if username else 'N/A'}
📅 Qo'shilgan: {date_str}
"""
                await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")
    
    await state.clear()


# ==========================================
# 📢 BROADCAST SECTION
# ==========================================

@admin_complete_router.message(F.text == "📢 Xabar yuborish", F.from_user.id.in_(ADMIN_ID))
async def broadcast_menu(message: Message, state: FSMContext):
    """Show broadcast menu"""
    await state.clear()  # Clear any existing state
    await message.answer(
        "📢 <b>XABAR YUBORISH</b>\n\n"
        "Xabar turini tanlang:",
        reply_markup=get_broadcast_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(F.data == "admin:broadcast:simple", F.from_user.id.in_(ADMIN_ID))
async def broadcast_simple_start(callback: CallbackQuery, state: FSMContext):
    """Start simple broadcast (copy message)"""
    await state.set_state(AdminStates.broadcast_simple)
    await callback.message.answer(
        "📬 <b>ODDIY XABAR YUBORISH</b>\n\n"
        "Yuboriladigan xabarni yuboring:\n"
        "(Matn, rasm, video, hujjat va h.k.)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:broadcast:forward", F.from_user.id.in_(ADMIN_ID))
async def broadcast_forward_start(callback: CallbackQuery, state: FSMContext):
    """Start forward broadcast"""
    await state.set_state(AdminStates.broadcast_forward)
    await callback.message.answer(
        "📨 <b>FORWARD XABAR YUBORISH</b>\n\n"
        "Forward qilinadigan xabarni yuboring:\n"
        "(Boshqa chatdan forward qiling yoki o'z xabaringizni yuboring)",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )
    await callback.answer()


@admin_complete_router.message(AdminStates.broadcast_simple, F.from_user.id.in_(ADMIN_ID))
async def broadcast_simple_received(message: Message, state: FSMContext):
    """Handle simple broadcast message received"""
    # Store message info in state
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id,
        broadcast_type='simple'
    )
    
    # Show preview and ask for confirmation
    await state.set_state(AdminStates.broadcast_confirm)
    
    await message.answer(
        "📬 <b>XABAR PREVIEW</b>\n\n"
        "Yuqoridagi xabarni barcha foydalanuvchilarga yuborishni xohlaysizmi?\n\n"
        "<i>Xabar ko'rinishini tekshirib, tasdiqlang:</i>",
        reply_markup=get_broadcast_confirm_menu('simple'),
        parse_mode="HTML"
    )


@admin_complete_router.message(AdminStates.broadcast_forward, F.from_user.id.in_(ADMIN_ID))
async def broadcast_forward_received(message: Message, state: FSMContext):
    """Handle forward broadcast message received"""
    # Store message info in state
    await state.update_data(
        broadcast_msg_id=message.message_id,
        broadcast_chat_id=message.chat.id,
        broadcast_type='forward'
    )
    
    # Show preview and ask for confirmation
    await state.set_state(AdminStates.broadcast_confirm)
    
    await message.answer(
        "📨 <b>FORWARD XABAR PREVIEW</b>\n\n"
        "Yuqoridagi xabarni barcha foydalanuvchilarga forward qilishni xohlaysizmi?\n\n"
        "<i>Xabar ko'rinishini tekshirib, tasdiqlang:</i>",
        reply_markup=get_broadcast_confirm_menu('forward'),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(
    F.data.startswith("admin:broadcast:confirm:"), 
    AdminStates.broadcast_confirm,
    F.from_user.id.in_(ADMIN_ID)
)
async def broadcast_confirm_handler(callback: CallbackQuery, state: FSMContext):
    """Handle broadcast confirmation (yes/no)"""
    action = callback.data.split(":")[3]  # yes or no
    
    if action == "no":
        # Cancel broadcast
        await state.clear()
        await callback.message.edit_text(
            "❌ <b>Xabar yuborish bekor qilindi</b>\n\n"
            "Xabar yuborilmadi.",
            parse_mode="HTML"
        )
        # Return to broadcast menu
        await callback.message.answer(
            "📢 <b>XABAR YUBORISH</b>",
            reply_markup=get_broadcast_menu(),
            parse_mode="HTML"
        )
        await callback.answer("Bekor qilindi")
        return
    
    # User confirmed - proceed with broadcast
    msg_type = callback.data.split(":")[4]  # simple or forward
    
    # Get stored message data
    data = await state.get_data()
    msg_id = data.get('broadcast_msg_id')
    chat_id = data.get('broadcast_chat_id')
    
    if not msg_id or not chat_id:
        await callback.message.edit_text(
            "❌ <b>Xatolik:</b> Xabar ma'lumotlari topilmadi. Iltimos, qayta urinib ko'ring.",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Get all users
    try:
        sql.execute("SELECT user_id FROM users WHERE is_blocked = FALSE")
        users = [row[0] for row in sql.fetchall()]
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Xatolik:</b> Foydalanuvchilar ro'yxatini olishda xatolik: {str(e)}",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    if not users:
        await callback.message.edit_text(
            "❌ <b>Xatolik:</b> Foydalanuvchilar topilmadi",
            parse_mode="HTML"
        )
        await state.clear()
        return
    
    # Update message to show sending status
    await callback.message.edit_text(
        f"📤 <b>XABAR YUBORILMOQDA...</b>\n\n"
        f"Foydalanuvchilar soni: {len(users)}\n"
        f"Xabar turi: {'📬 Oddiy' if msg_type == 'simple' else '📨 Forward'}\n\n"
        f"⏳ Boshlanmoqda...",
        parse_mode="HTML"
    )
    await callback.answer("Yuborish boshlandi")
    
    # Send broadcast
    status_msg = await callback.message.answer(
        f"📤 Yuborilmoqda... 0/{len(users)}\n✅ 0 | ❌ 0"
    )
    
    success = 0
    failed = 0
    
    for i, user_id in enumerate(users):
        try:
            if msg_type == 'simple':
                # Copy message (simple broadcast)
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=chat_id,
                    message_id=msg_id
                )
            else:
                # Forward message
                await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=chat_id,
                    message_id=msg_id
                )
            success += 1
        except Exception as e:
            failed += 1
            # Log failed users for potential retry
            print(f"[BROADCAST] Failed to send to {user_id}: {e}")
        
        # Update status every 50 users
        if i % 50 == 0 or i == len(users) - 1:
            try:
                await status_msg.edit_text(
                    f"📤 Yuborilmoqda... {i+1}/{len(users)}\n"
                    f"✅ {success} | ❌ {failed}"
                )
            except:
                pass
        
        # Small delay to avoid rate limits
        await asyncio.sleep(0.05)
    
    # Final status
    await status_msg.edit_text(
        f"✅ <b>TUGADI!</b>\n\n"
        f"📤 Yuborildi: {success}\n"
        f"❌ Yuborilmadi: {failed}\n"
        f"📊 Jami: {len(users)}"
    )
    
    # Clear state
    await state.clear()
    
    # Return to broadcast menu
    await callback.message.answer(
        "📢 <b>XABAR YUBORISH</b>\n\n"
        "Yana xabar yuborish uchun turini tanlang:",
        reply_markup=get_broadcast_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.message(F.text == "❌ Bekor qilish", F.from_user.id.in_(ADMIN_ID))
async def broadcast_cancel(message: Message, state: FSMContext):
    """Cancel broadcast at any stage"""
    current_state = await state.get_state()
    if current_state in [AdminStates.broadcast_simple.state, 
                         AdminStates.broadcast_forward.state,
                         AdminStates.broadcast_confirm.state]:
        await state.clear()
        await message.answer(
            "❌ <b>Xabar yuborish bekor qilindi</b>",
            reply_markup=get_admin_main_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🔙 Asosiy menyu",
            reply_markup=get_admin_main_menu()
        )


# ==========================================
# 🔧 CHANNELS SECTION
# ==========================================

@admin_complete_router.message(F.text == "🔧 Kanallar", F.from_user.id.in_(ADMIN_ID))
async def channels_menu(message: Message):
    """Show channels menu"""
    await message.answer(
        "🔧 <b>KANALLAR BOSHQARUVI</b>",
        reply_markup=get_channels_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(F.data == "admin:channel:list", F.from_user.id.in_(ADMIN_ID))
async def channels_list(callback: CallbackQuery):
    """List channels"""
    try:
        sql.execute("SELECT chat_id, username, title FROM mandatorys")
        channels = sql.fetchall()
        
        if not channels:
            text = "📭 Hozircha kanallar yo'q"
        else:
            text = "📋 <b>KANALLAR RO'YXATI</b>\n\n"
            for chat_id, username, title in channels:
                text += f"📢 {title or 'N/A'}\n"
                text += f"   @{username or 'N/A'}\n"
                text += f"   ID: <code>{chat_id}</code>\n\n"
    except Exception as e:
        text = f"❌ Xatolik: {str(e)}"
    
    await callback.message.edit_text(text, reply_markup=get_channels_menu(), parse_mode="HTML")
    await callback.answer()


@admin_complete_router.callback_query(F.data == "admin:channel:add", F.from_user.id.in_(ADMIN_ID))
async def channel_add_prompt(callback: CallbackQuery, state: FSMContext):
    """Prompt for channel add"""
    await state.set_state(AdminStates.channel_add)
    await callback.message.answer(
        "➕ Kanal qo'shish\n\n"
        "Kanal username yuboring (@kanal_username):"
    )
    await callback.answer()


@admin_complete_router.message(AdminStates.channel_add, F.from_user.id.in_(ADMIN_ID))
async def channel_add_execute(message: Message, state: FSMContext):
    """Execute channel add"""
    username = message.text.strip()
    
    if not username.startswith('@'):
        await message.answer("❌ Username @ bilan boshlanishi kerak")
        return
    
    try:
        chat = await bot.get_chat(username)
        chat_id = chat.id
        
        # Get invite link
        try:
            invite_link = await bot.export_chat_invite_link(chat_id)
        except:
            invite_link = None
        
        # Save to database
        sql.execute(
            "INSERT INTO mandatorys (chat_id, username, title, types) VALUES (%s, %s, %s, %s) ON CONFLICT (chat_id) DO UPDATE SET username = EXCLUDED.username",
            (chat_id, username, chat.title, 'channel')
        )
        db.commit()
        
        await message.answer(f"✅ Kanal qo'shildi:\n📢 {chat.title}\n🔗 {invite_link or 'N/A'}")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}\n\nBot kanalga admin qilinganmi?")
    
    await state.clear()


@admin_complete_router.callback_query(F.data == "admin:channel:delete", F.from_user.id.in_(ADMIN_ID))
async def channel_delete_prompt(callback: CallbackQuery):
    """Prompt for channel delete"""
    try:
        sql.execute("SELECT chat_id, username, title FROM mandatorys")
        channels = sql.fetchall()
        
        if not channels:
            await callback.answer("Kanallar yo'q", show_alert=True)
            return
        
        # Create keyboard with channels
        buttons = []
        for chat_id, username, title in channels:
            buttons.append([InlineKeyboardButton(
                text=f"❌ {title or username}",
                callback_data=f"admin:channel:del:{chat_id}"
            )])
        buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:channel:list")])
        
        await callback.message.edit_text(
            "❌ O'chiriladigan kanalni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    except Exception as e:
        await callback.answer(f"Xatolik: {str(e)}", show_alert=True)


@admin_complete_router.callback_query(F.data.startswith("admin:channel:del:"), F.from_user.id.in_(ADMIN_ID))
async def channel_delete_execute(callback: CallbackQuery):
    """Execute channel delete"""
    chat_id = int(callback.data.split(":")[3])
    
    try:
        sql.execute("DELETE FROM mandatorys WHERE chat_id = %s", (chat_id,))
        db.commit()
        await callback.answer("✅ Kanal o'chirildi!")
        await channels_list(callback)
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}", show_alert=True)


# ==========================================
# 🎮 GAMIFICATION SECTION
# ==========================================

@admin_complete_router.message(F.text == "🎮 Gamification", F.from_user.id.in_(ADMIN_ID))
async def gamification_menu(message: Message):
    """Show gamification menu"""
    await message.answer(
        "🎮 <b>GAMIFICATION</b>",
        reply_markup=get_gamification_menu(),
        parse_mode="HTML"
    )


@admin_complete_router.callback_query(F.data == "admin:game:achievements", F.from_user.id.in_(ADMIN_ID))
async def game_achievements(callback: CallbackQuery):
    """Show achievements management"""
    text = """
🏆 <b>YUTUQLAR BOSHQARUVI</b>

Bu bo'lim tez orada qo'shiladi.
"""
    await callback.message.edit_text(text, reply_markup=get_gamification_menu(), parse_mode="HTML")
    await callback.answer("Tez orada!")


@admin_complete_router.callback_query(F.data == "admin:game:daily", F.from_user.id.in_(ADMIN_ID))
async def game_daily(callback: CallbackQuery):
    """Show daily challenge management"""
    text = """
🎯 <b>KUNLIK VAZIFALAR</b>

Bu bo'lim tez orada qo'shiladi.
"""
    await callback.message.edit_text(text, reply_markup=get_gamification_menu(), parse_mode="HTML")
    await callback.answer("Tez orada!")


# ==========================================
# 🔙 BACK HANDLER
# ==========================================

@admin_complete_router.callback_query(F.data == "admin:back", F.from_user.id.in_(ADMIN_ID))
async def admin_back(callback: CallbackQuery):
    """Back to admin main"""
    await callback.message.delete()
    await callback.answer()


@admin_complete_router.message(F.text == "🔙 Chiqish", F.from_user.id.in_(ADMIN_ID))
async def admin_exit(message: Message):
    """Exit admin panel"""
    from src.keyboards.buttons import UserPanels
    await message.answer(
        "👋 Admin paneldan chiqdingiz.",
        reply_markup=await UserPanels.user_main_menu()
    )


# ==========================================
# 🔙 ORQAGA QAYTISH (Universal)
# ==========================================

@admin_complete_router.message(F.text == "🔙Orqaga qaytish", F.from_user.id.in_(ADMIN_ID))
async def universal_back(message: Message, state: FSMContext):
    """Universal back button"""
    await state.clear()
    await message.answer("🔙 Asosiy menyu", reply_markup=get_admin_main_menu())
