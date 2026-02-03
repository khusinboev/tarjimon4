from datetime import datetime, timedelta

import psycopg2
import pytz
from aiogram import Router, F
from aiogram.exceptions import AiogramError
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, KeyboardButton as RButton, \
    KeyboardButtonRequestChat, ChatInviteLink
from aiogram.enums import ChatType
from aiogram.fsm.state import StatesGroup, State
from dateutil.relativedelta import relativedelta

from src.db.init_db import init_languages_table
from src.keyboards.buttons import AdminPanel
from config import sql, ADMIN_ID, bot, DB_CONFIG
from src.keyboards.keyboard_func import PanelFunc

admin_router = Router()

class Form(StatesGroup):
    ch_add = State()
    for_username = State()
    ch_delete = State()

    anons_forward = State()
    anons_simple = State()

    clear_base = State()


# Admin panelga kirish - Note: /admin is now handled by admin_panel_complete.py
# This handler serves as backup for /panel command
@admin_router.message(Command("panel"), F.from_user.id.in_(ADMIN_ID), F.chat.type == ChatType.PRIVATE)
async def panel_handler(message: Message) -> None:
    from src.keyboards.buttons import AdminPanel
    await message.answer("Admin panel", reply_markup=await AdminPanel.admin_menu())


markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text="🔙Orqaga qaytish")]])
@admin_router.message(F.text == "🔙Orqaga qaytish", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def backs(message: Message, state: FSMContext):
    await message.reply("Orqaga qaytildi", reply_markup=await AdminPanel.admin_menu())
    await state.clear()

def get_flag(lang_code: str) -> str:
    """Lang code asosida bayroq chiqarish (agar mumkin bo‘lsa)"""
    if not lang_code or len(lang_code) != 2:
        return "🌐"
    lang_code = lang_code.upper()
    return chr(127397 + ord(lang_code[0])) + chr(127397 + ord(lang_code[1]))
# Statistika
@admin_router.message(F.text == "📊Statistika", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def new(message: Message):
    now = datetime.now(pytz.timezone("Asia/Tashkent")).date()

    # Oxirgi 3 oy: joriy oy va undan oldingi 2 ta oy
    current_month = now.replace(day=1)
    months = [current_month - relativedelta(months=i) for i in range(3)]

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Jami foydalanuvchilar
    cur.execute("SELECT COUNT(*) FROM users WHERE is_active = TRUE")
    all_users = cur.fetchone()[0]

    # Oxirgi 3 oydagi jami foydalanuvchilar
    cur.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) >= %s", (months[-1],))
    last_3_months = cur.fetchone()[0]

    # Har bir oy bo‘yicha statistikalar
    month_counts = {}
    for month in months:
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at) >= %s AND DATE(created_at) < %s",
            (month, month + relativedelta(months=1))
        )
        month_counts[month.strftime("%B")] = cur.fetchone()[0] or 0

    # Oxirgi 7 kun statistikasi
    last_7_days = {}
    for i in range(7):
        date_str = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        cur.execute("SELECT COUNT(*) FROM users WHERE DATE(created_at) = %s", (date_str,))
        last_7_days[date_str] = cur.fetchone()[0] or 0

    # --- Yangi qo'shiladigan qism: tillar kesimi ---
    cur.execute("SELECT interface_lang, COUNT(*) FROM users GROUP BY interface_lang ORDER BY COUNT(*) DESC")
    lang_stats = cur.fetchall()


    # Xabarni tayyorlash (asosiy statistikalar)
    stats_text = (
        f"📊 *Foydalanuvchi Statistikasi:*\n\n"
        f"🔹 *Jami foydalanuvchilar:* {all_users}\n\n"
        f"📅 *Oxirgi 3 oy:* (Jami {last_3_months} ta)\n"
    )
    for month, count in month_counts.items():
        stats_text += f" - {month}: {count} ta\n"

    stats_text += "\n📆 *Oxirgi 7 kun:* (Jami {})\n".format(sum(last_7_days.values()))
    for day, count in last_7_days.items():
        stats_text += f" - {day}: {count} ta\n"

    await message.answer(stats_text, parse_mode="Markdown")

    # # --- Tillar kesimi xabari ---
    # langs_text = "🌐 *Foydalanuvchilar tillar bo‘yicha:*\n\n"
    # for lang_code, count in lang_stats:
    #     flag = get_flag(lang_code) if lang_code else "🌐"
    #     langs_text += f" - {flag} {lang_code or 'None'}: {count} ta\n"
    #
    # # Agar matn 4096 belgidan oshsa bo‘lib yuboramiz
    # max_len = 4000
    # parts = [langs_text[i:i + max_len] for i in range(0, len(langs_text), max_len)]
    # for part in parts:
    #     await message.answer(part, parse_mode="Markdown")
    # --- Oxirgi 48 soatda tillar kesimi (TOP 10) ---
    cur.execute("""
        SELECT interface_lang, COUNT(*) 
        FROM users 
        WHERE created_at >= NOW() - interval '48 hours'
        GROUP BY interface_lang 
        ORDER BY COUNT(*) DESC 
        LIMIT 10
    """)
    lang_last_48 = cur.fetchall()

    # --- Xabar matni ---
    langs_48_text = "⏰ *Oxirgi 48 soatda qo‘shilganlar (TOP 10 tillar):*\n\n"
    for interface_lang, count in lang_last_48:
        flag = get_flag(interface_lang) if interface_lang else "🌐"
        langs_48_text += f" - {flag} {interface_lang or 'None'}: {count} ta\n"

    await message.answer(langs_48_text, parse_mode="Markdown") 


# Kanallar bo'limi
@admin_router.message(F.text == '🔧Kanallar', F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def new(msg: Message):
    await msg.answer("Tanlang", reply_markup=await AdminPanel.admin_channel())


@admin_router.message(F.text == "🔙Orqaga qaytish", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID), Form.ch_add or Form.ch_delete)
async def backs(message: Message, state: FSMContext):
    await message.reply("Orqaga qaytildi", reply_markup=await AdminPanel.admin_channel())
    await state.clear()


@admin_router.message(F.text == "➕Kanal qo'shish", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_add(message: Message, state: FSMContext):
    keyboard = []
    keyboard.extend([
        [KeyboardButton(text="🔙Orqaga qaytish")]
    ])
    await bot.send_message(message.chat.id,
                            text="Kanal ulash bo'limi. \nBotga kanal ulashning 3 ta usuli bor:\n"
                                 "1. https://t.me/coder_admin kanal havolasini shu tartibda yuboring.\n"
                                 "2. @coder_admin username ni shu tartibda yuboring",
                            reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True),
                            parse_mode="html")
    await state.set_state(Form.ch_add)


@admin_router.message(Form.ch_add, F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_add1(message: Message, state: FSMContext):
    if message.chat_shared:
        pass
        # try:
        #     chat = await bot.get_chat(message.chat_shared.chat_id)
        #     invite_link: ChatInviteLink = await bot.create_chat_invite_link(chat_id=chat.id, name="KINOMTV_UZ")
        #     link = invite_link.invite_link
        # except AiogramError:
        #     await state.clear()
        #     await bot.send_message(chat_id=message.chat.id,
        #                            text="Bot kanalga <b>admin emas!</b> Iltimos admin qilib keyin urinib ko'ring",
        #                            reply_markup=await AdminPanel.admin_channel(),
        #                            parse_mode="html")
        # else:
        #     channel_id = chat.id
        #     sql.execute(f"SELECT chat_id FROM public.mandatorys WHERE chat_id = {channel_id}")
        #     data = sql.fetchone()
        #     if data is None:
        #         await PanelFunc.channel_add(channel_id, link)
        #         await state.clear()
        #         await message.reply("Kanal qo'shildi🎉🎉", reply_markup=await AdminPanel.admin_channel())
        #
        #     else:
        #         await message.reply("Bu kanal avvaldan bor", reply_markup=await AdminPanel.admin_channel())
        #     await state.clear()
    elif "https://t.me/" in message.text:
        chat_link = "@"+message.text.split("https://t.me/", 1)[1]
        try:
            chat = await bot.get_chat(chat_link)
        except Exception as e:
            print(e)
            await state.clear()
            await bot.send_message(chat_id=message.chat.id,
                                   text="Bot kanalga <b>admin emas!</b> yoki havolani qayta ishlashda muammolar bo'lyapti. Iltimos havolani va adminlikni tekshirib qaytadan urining",
                                   reply_markup=await AdminPanel.admin_channel(),
                                   parse_mode="html")
        else:
            channel_id = chat.id
            sql.execute(f"SELECT chat_id FROM public.mandatorys WHERE chat_id = {channel_id}")
            data = sql.fetchone()
            if data is None:
                await message.reply("Kanal username qabul qilindi, endi taklif havolasini yuboring. U https://t.me/+ deb boshlanadi. Buni kanal havolalari bo'limida yaratasiz.", reply_markup=markup)
                await state.update_data(channel_id=str(channel_id))
                await state.set_state(Form.for_username)

            else:
                await message.reply("Bu kanal avvaldan bor, qaytadan yuboring", reply_markup=markup)
    elif message.text[0] == "@":
        chat_link = "@"+message.text[1:]
        try:
            chat = await bot.get_chat(chat_link)
        except Exception:
            await state.clear()
            await bot.send_message(chat_id=message.chat.id,
                                   text="Bot kanalga <b>admin emas!</b> yoki havolani qayta ishlashda muammolar bo'lyapti. Iltimos havolani va adminlikni tekshirib qaytadan urining",
                                   reply_markup=await AdminPanel.admin_channel(),
                                   parse_mode="html")
        else:
            channel_id = chat.id
            sql.execute(f"SELECT chat_id FROM public.mandatorys WHERE chat_id = {channel_id}")
            data = sql.fetchone()
            if data is None:
                await message.reply(
                    "Kanal username qabul qilindi, endi taklif havolasini yuboring. U https://t.me/+ deb boshlanadi. Buni kanal havolalari bo'limida yaratasiz.",
                    reply_markup=markup)
                await state.update_data(channel_id=str(channel_id))
                await state.set_state(Form.for_username)

            else:
                await message.reply("Bu kanal avvaldan bor, qaytadan yuboring", reply_markup=markup)
    else:
        await message.answer("Kanal <b>username</b> yuboring", reply_markup=markup, parse_mode="html")

@admin_router.message(Form.for_username, F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_add1(message: Message, state: FSMContext):
    link = message.text
    if "https://t.me/" in link:
        data = await state.get_data()
        channel_id = data["channel_id"]
        await PanelFunc.channel_add(channel_id, link)
        await state.clear()
        await message.reply("Kanal qo'shildi🎉🎉", reply_markup=await AdminPanel.admin_channel())
    else:
        await message.answer(
            "Kanal taklif havolasini yuboring. U https://t.me/+ deb boshlanadi. Buni kanal havolalari bo'limida yaratasiz.",
            reply_markup=markup)


@admin_router.message(F.text == "❌Kanalni olib tashlash", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_delete(message: Message, state: FSMContext):
    await message.reply("O'chiriladigan kanalning userini yuboring.\nMisol uchun @coder_admin", reply_markup=markup)
    await state.set_state(Form.ch_delete)


@admin_router.message(Form.ch_delete, F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_delete2(message: Message, state: FSMContext):
    all_details = await bot.get_chat(message.text)
    channel_id = all_details.id
    sql.execute(f"""SELECT chat_id FROM public.mandatorys WHERE chat_id = '{channel_id}'""")
    data = sql.fetchone()

    if data is None:
        await message.reply("Bunday kanal yo'q", reply_markup=await AdminPanel.admin_channel())
    else:
        if message.text[0] == '@':
            await PanelFunc.channel_delete(channel_id)
            await state.clear()
            await message.reply("Kanal muvaffaqiyatli o'chirildi", reply_markup=await AdminPanel.admin_channel())
        else:
            await message.reply("Kanal useri xato kiritildi\nIltimos userni @coder_admin ko'rinishida kiriting",
                                reply_markup=await AdminPanel.admin_channel())

    await state.clear()


@admin_router.message(F.text == "📋 Kanallar ro'yxati", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def channel_list(message: Message):
    if len(await PanelFunc.channel_list()) > 3:
        await message.answer(await PanelFunc.channel_list(), parse_mode='html')
    else:
        await message.answer("Hozircha kanallar yo'q")


@admin_router.message(F.text == "📊Tillar", F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def new(message: Message):
    status = init_languages_table()
    if status:
        await message.answer("Ma'lumotlar yangilandi")
    else:
        await message.answer("O'zgarishlar bo'lmadi")


# ==================== ADMIN STATISTIKA ====================

@admin_router.message(Command("adminstats"), F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def admin_statistics(message: Message):
    """Admin uchun to'liq statistika"""
    try:
        # Umumiy foydalanuvchilar soni
        sql.execute("SELECT COUNT(*) FROM users")
        total_users = sql.fetchone()[0]
        
        # Bugun qo'shilgan foydalanuvchilar
        sql.execute("""
            SELECT COUNT(*) FROM users 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        today_users = sql.fetchone()[0]
        
        # Faol foydalanuvchilar (oxirgi 7 kun ichida)
        sql.execute("""
            SELECT COUNT(DISTINCT user_id) FROM translation_history 
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        active_users = sql.fetchone()[0]
        
        # Jami tarjimalar soni
        sql.execute("SELECT COUNT(*) FROM translation_history")
        total_translations = sql.fetchone()[0]
        
        # Bugungi tarjimalar
        sql.execute("""
            SELECT COUNT(*) FROM translation_history 
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        today_translations = sql.fetchone()[0]
        
        # Eng faol foydalanuvchi
        sql.execute("""
            SELECT user_id, COUNT(*) as trans_count 
            FROM translation_history 
            GROUP BY user_id 
            ORDER BY trans_count DESC 
            LIMIT 1
        """)
        top_user_row = sql.fetchone()
        top_user = f"{top_user_row[0]} ({top_user_row[1]} tarjima)" if top_user_row else "Ma'lumot yo'q"
        
        # Eng ko'p ishlatiladigan til juftligi
        sql.execute("""
            SELECT from_lang, to_lang, COUNT(*) as usage_count 
            FROM translation_history 
            GROUP BY from_lang, to_lang 
            ORDER BY usage_count DESC 
            LIMIT 1
        """)
        top_lang_pair_row = sql.fetchone()
        top_lang_pair = f"{top_lang_pair_row[0]} → {top_lang_pair_row[1]} ({top_lang_pair_row[2]}x)" if top_lang_pair_row else "Ma'lumot yo'q"
        
        # Oxirgi 24 soat ichidagi tarjimalar
        sql.execute("""
            SELECT COUNT(*) FROM translation_history 
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        last_24h_translations = sql.fetchone()[0]
        
        text = (
            "👨‍💼 <b>ADMIN STATISTIKASI</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👥 <b>FOYDALANUVCHILAR:</b>\n"
            f"├ Jami: <b>{total_users}</b>\n"
            f"├ Bugun qo'shildi: <b>{today_users}</b>\n"
            f"└ Faol (7 kun): <b>{active_users}</b>\n\n"
            "🔄 <b>TARJIMALAR:</b>\n"
            f"├ Jami tarjimalar: <b>{total_translations}</b>\n"
            f"├ Bugun: <b>{today_translations}</b>\n"
            f"└ 24 soat: <b>{last_24h_translations}</b>\n\n"
            "📊 <b>TOP MA'LUMOTLAR:</b>\n"
            f"├ Eng faol user: <code>{top_user}</code>\n"
            f"└ Top til: <code>{top_lang_pair}</code>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🕐 <i>{datetime.now().strftime('%d.%m.%Y %H:%M')}</i>"
        )
        
        await message.answer(text, parse_mode="HTML")
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Statistikani yuklashda xatolik:</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )


@admin_router.message(Command("adminlogs"), F.chat.type == ChatType.PRIVATE, F.from_user.id.in_(ADMIN_ID))
async def admin_view_logs(message: Message):
    """Oxirgi loglarni ko'rish"""
    try:
        import os
        log_file = "logs/bot_errors.log"
        
        if not os.path.exists(log_file):
            await message.answer("❌ Log fayli topilmadi!")
            return
        
        # Oxirgi 30 qatorni o'qish
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            last_lines = lines[-30:] if len(lines) > 30 else lines
        
        if not last_lines:
            await message.answer("📭 Log fayli bo'sh")
            return
        
        log_text = "".join(last_lines)
        
        # Telegram xabar limitiga mos kelishi uchun
        if len(log_text) > 4000:
            log_text = log_text[-4000:]
        
        await message.answer(
            f"📋 <b>OXIRGI ERRORLAR:</b>\n\n"
            f"<pre>{log_text}</pre>",
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(
            f"❌ <b>Loglarni o'qishda xatolik:</b>\n\n"
            f"<code>{str(e)}</code>",
            parse_mode="HTML"
        )