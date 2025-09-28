import asyncio
import random
import os
from typing import List, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from openpyxl import Workbook
from config import db

router = Router()

# =====================================================
# 🔌 Localization (unchanged)
# =====================================================
LOCALES = {
    "uz": {
        "cabinet": "📚 Kabinet",
        "choose_lang": "Tilni tanlang:",
        "my_books": "📖 Lug'atlarim",
        "practice": "🏋️ Mashq",
        "public_vocabs": "🌐 Ommaviy lug'atlar",
        "settings": "⚙️ Sozlamalar",
        "back": "🔙 Orqaga",
        "add_words": "➕ So'z qo'shish",
        "delete": "❌ O'chirish",
        "export": "📤 Eksport",
        "confirm_delete": "❓ Ushbu lug'atni o'chirishga ishonchingiz komilmi?",
        "yes": "✅ Ha",
        "no": "❌ Yo'q",
        "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}",
        "results_header": "📊 Batafsil natijalar:",
        "results_lines": (
            "🔹 Savollar soni: {unique}\n"
            "🔹 Jami berilgan savollar: {answers}\n"
            "✅ To'g'ri javoblar: {correct}\n"
            "❌ Xato javoblar: {wrong}\n"
            "📊 Natijaviy ko'rsatgich: {percent:.1f}%"
        ),
        "no_books": "Sizda hali lug'at yo'q.",
        "enter_book_name": "Yangi lug'at nomini kiriting:",
        "book_created": "✅ Lug'at yaratildi: {name} (id={id})",
        "book_exists": "❌ Bu nom bilan lug'at mavjud.",
        "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).",
        "added_pairs": "✅ {n} ta juftlik qo'shildi. Yana yuborishingiz mumkin 👇",
        "empty_book": "❌ Bu lug'atda yetarli so'zlar yo'q (kamida 4 ta kerak).",
        "question": "❓ {word}",
        "correct": "✅ To'g'ri",
        "wrong": "❌ Xato. To'g'ri javob: {correct}",
        "finish": "🏁 Tugatish",
        "session_end": "Mashq tugadi.",
        "back_to_book": "🔙 Orqaga",
        "main_menu": "🏠 Bosh menyu",
        "cancel": "❌ Bekor qilish",
    },
    "en": {
        "cabinet": "📚 Cabinet",
        "choose_lang": "Choose your language:",
        "my_books": "📖 My vocabularies",
        "practice": "🏋️ Practice",
        "public_vocabs": "🌐 Public vocabularies",
        "settings": "⚙️ Settings",
        "back": "🔙 Back",
        "add_words": "➕ Add words",
        "delete": "❌ Delete",
        "export": "📤 Export",
        "confirm_delete": "❓ Are you sure you want to delete this book?",
        "yes": "✅ Yes",
        "no": "❌ No",
        "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}",
        "results_header": "📊 Detailed Results:",
        "results_lines": (
            "🔹 Questions in set: {unique}\n"
            "🔹 Total asked: {answers}\n"
            "✅ Correct: {correct}\n"
            "❌ Wrong: {wrong}\n"
            "📊 Performance: {percent:.1f}%"
        ),
        "no_books": "You have no books yet.",
        "enter_book_name": "Enter new book name:",
        "book_created": "✅ Book created: {name} (id={id})",
        "book_exists": "❌ Book with this name already exists.",
        "send_pairs": "Send word pairs (each line: word-translation).",
        "added_pairs": "✅ {n} pairs added. You can send more 👇",
        "empty_book": "❌ This book doesn't have enough words (min 4).",
        "question": "❓ {word}",
        "correct": "✅ Correct",
        "wrong": "❌ Wrong. Correct: {correct}",
        "finish": "🏁 Finish",
        "session_end": "Practice finished.",
        "back_to_book": "🔙 Back",
        "main_menu": "🏠 Main menu",
        "cancel": "❌ Cancel",
    }
}

# =====================================================
# 🔌 Database helpers (optimized)
# =====================================================

async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False):
    def run():
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            if many:
                rows = cur.fetchall()
                if not rows:
                    return []
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, r)) for r in rows]
            else:
                row = cur.fetchone()
                if not row:
                    return None
                cols = [d[0] for d in cur.description]
                return dict(zip(cols, row))
        db.commit()
        return None
    return await asyncio.to_thread(run)

async def get_user_data(user_id: int) -> Dict[str, Any]:
    """Fetch user lang and books in one query batch for optimization."""
    lang_row = await db_exec(
        "SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (user_id,), fetch=True
    )
    lang = lang_row["lang_code"] if lang_row else "uz"
    books = await db_exec(
        "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,), fetch=True, many=True
    )
    return {"lang": lang, "books": books or []}

async def set_user_lang(user_id: int, lang: str):
    row = await db_exec(
        "SELECT id FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (user_id,), fetch=True
    )
    if row:
        await db_exec("UPDATE accounts SET lang_code=%s WHERE id=%s", (lang, row["id"]))
    else:
        await db_exec("INSERT INTO accounts (user_id, lang_code) VALUES (%s,%s)", (user_id, lang))

# =====================================================
# 🔌 UI Builders (optimized)
# =====================================================
def two_col_rows(buttons: List[InlineKeyboardButton]) -> List[List[InlineKeyboardButton]]:
    rows = []
    for i in range(0, len(buttons), 2):
        row = buttons[i:i+2]
        rows.append(row)
    return rows

def get_locale(lang: str) -> Dict[str, str]:
    return LOCALES.get(lang, LOCALES["uz"])

def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    """Asosiy kabinet menyu klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="mashq:list")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="lughat:list"),
         InlineKeyboardButton(text=L["public_vocabs"], callback_data="ommaviy:list")],
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")
        ],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
    ])

# =====================================================
# 🔌 Export helper (optimized)
# =====================================================
async def export_book_to_excel(book_id: int, user_id: int) -> str:
    rows = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id",
        (book_id,), fetch=True, many=True
    )
    if len(rows) < 1:
        return None

    wb = Workbook()
    ws = wb.active
    ws.title = "Vocabulary"
    ws.append(["Word", "Translation"])
    for r in rows:
        ws.append([r["word_src"], r["word_trg"]])

    file_path = f"export_{user_id}_{book_id}.xlsx"
    wb.save(file_path)
    return file_path

# =====================================================
# 🔌 Helper to send message
# =====================================================
async def safe_edit_or_send(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup, lang: str):
    """Delete old message and send new to avoid edit issues with old inlines."""
    try:
        await cb.message.delete()
    except:
        pass
    await cb.message.answer(text, reply_markup=kb)

# =====================================================
# 🔌 Cabinet menu (main)
# =====================================================

@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    data = await get_user_data(msg.from_user.id)
    L = get_locale(data["lang"])
    await msg.answer(L["cabinet"], reply_markup=cabinet_kb(data["lang"]))

@router.callback_query(lambda c: c.data and c.data.startswith("cab:"))
async def cb_cabinet(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    if cb.data == "cab:settings":
        await safe_edit_or_send(cb, L["choose_lang"], settings_kb(lang), lang)

    elif cb.data == "cab:back":
        await safe_edit_or_send(cb, L["cabinet"], cabinet_kb(lang), lang)

    try:
        await cb.answer()
    except:
        pass

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = get_locale(lang)
    await safe_edit_or_send(cb, L["cabinet"], cabinet_kb(lang), lang)
    await cb.answer()