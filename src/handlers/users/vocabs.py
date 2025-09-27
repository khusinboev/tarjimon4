import asyncio
import random
import os
from typing import List, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from openpyxl import Workbook
from config import db

router = Router()

# =====================================================
# 📌 Localization
# =====================================================
LOCALES = {
    "uz": {
        "cabinet": "📚 Kabinet",
        "choose_lang": "Tilni tanlang:",
        "my_books": "📖 Lug'atlarim",
        "new_book": "➕ Yangi lug'at",
        "settings": "⚙️ Sozlamalar",
        "back": "🔙 Orqaga",
        "practice": "▶ Mashq",
        "add_words": "➕ So'z qo'shish",
        "delete": "❌ O‘chirish",
        "export": "📤 Eksport",
        "confirm_delete": "❓ Ushbu lug‘atni o‘chirishga ishonchingiz komilmi?",
        "yes": "✅ Ha",
        "no": "❌ Yo‘q",
        "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}",
        "results_header": "📊 Batafsil natijalar:",
        "results_lines": (
            "🔹 Savollar soni: {unique}\n"
            "🔹 Jami berilgan savollar: {answers}\n"
            "✅ To‘g‘ri javoblar: {correct}\n"
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
        "wrong": "❌ Xato. To‘g‘ri javob: {correct}",
        "finish": "🏁 Tugatish",
        "session_end": "Mashq tugadi.",
        "back_to_book": "🔙 Orqaga",
        "main_menu": "🏠 Bosh menyu",
        "cancel": "❌ Bekor qilish",
        "make_public": "🌐 Global qilish",
        "make_private": "🔒 Local qilish",
        "public_books": "🌐 Umumiy lug'atlar",
        "toggle_confirm": "❓ O'zgartirishni tasdiqlaysizmi?",
        "toggled_public": "✅ Lug'at global qilindi.",
        "toggled_private": "✅ Lug'at local qilindi.",
        "no_public_books": "Hali umumiy lug'atlar yo'q.",
        "practice_section": "▶ Mashq bo'limi",
        "lang_changed": "✅ Til o'zgartirildi.",
    },
    "en": {
        "cabinet": "📚 Cabinet",
        "choose_lang": "Choose your language:",
        "my_books": "📖 My books",
        "new_book": "➕ New book",
        "settings": "⚙️ Settings",
        "back": "🔙 Back",
        "practice": "▶ Practice",
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
        "make_public": "🌐 Make Global",
        "make_private": "🔒 Make Local",
        "public_books": "🌐 Public Books",
        "toggle_confirm": "❓ Confirm change?",
        "toggled_public": "✅ Book made global.",
        "toggled_private": "✅ Book made local.",
        "no_public_books": "No public books yet.",
        "practice_section": "▶ Practice Section",
        "lang_changed": "✅ Language changed.",
    }
}

# =====================================================
# 📌 Database helpers
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
    lang_row = await db_exec(
        "SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (user_id,), fetch=True
    )
    lang = lang_row["lang_code"] if lang_row else "uz"
    books = await db_exec(
        "SELECT id, name, is_public FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,), fetch=True, many=True
    )
    return {"lang": lang, "books": books or []}

async def get_book_details(book_id: int) -> Dict[str, Any]:
    return await db_exec(
        "SELECT id, name, user_id, is_public FROM vocab_books WHERE id=%s",
        (book_id,), fetch=True
    )

def get_locale(lang: str) -> Dict[str, str]:
    return LOCALES.get(lang, LOCALES["uz"])

# =====================================================
# 📌 States
# =====================================================
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# =====================================================
# 📌 Helper Functions
# =====================================================
def two_col_rows(buttons: List[InlineKeyboardButton]) -> List[List[InlineKeyboardButton]]:
    return [buttons[i:i+2] for i in range(0, len(buttons), 2)]

async def export_book_to_excel(book_id: int, user_id: int) -> str:
    entries = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s",
        (book_id,), fetch=True, many=True
    )
    book = await get_book_details(book_id)
    if not book:
        raise ValueError("Book not found")

    wb = Workbook()
    ws = wb.active
    ws.title = book["name"]
    ws.append(["Source Word", "Target Word"])
    for e in entries:
        ws.append([e["word_src"], e["word_trg"]])

    file_path = f"book_{book_id}.xlsx"
    wb.save(file_path)
    return file_path

# =====================================================
# 📌 Keyboards
# =====================================================
def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books"),
         InlineKeyboardButton(text=L["public_books"], callback_data="cab:public_books")],
        [InlineKeyboardButton(text=L["practice_section"], callback_data="cab:practice"),
         InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")],
    ])

def books_kb(books: List[Dict], lang: str, practice_mode: bool = False) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    buttons = [
        InlineKeyboardButton(
            text=f"{b['name']} {'🌐' if b.get('is_public', False) else '🔒'} (id={b['id']})",
            callback_data=f"{'practice_book' if practice_mode else 'book'}:{b['id']}"
        ) for b in books
    ]
    rows = two_col_rows(buttons)
    if not practice_mode:
        rows.append([InlineKeyboardButton(text=L["new_book"], callback_data="cab:new")])
    rows.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def book_kb(book_id: int, lang: str, is_public: bool, is_owner: bool) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    rows = [
        [InlineKeyboardButton(text=L["practice"], callback_data=f"book:practice:{book_id}")],
        [InlineKeyboardButton(text=L["export"], callback_data=f"book:export:{book_id}")]
    ]
    if is_owner:
        rows.insert(1, [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")])
        rows.append([InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete:{book_id}")])
        toggle_text = L["make_private"] if is_public else L["make_public"]
        rows.append([InlineKeyboardButton(text=toggle_text, callback_data=f"book:toggle_public:{book_id}")])
    rows.append([InlineKeyboardButton(text=L["back"], callback_data="cab:books")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
    ])

# =====================================================
# 📌 Handlers (asosiylari)
# =====================================================
@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    data = await get_user_data(msg.from_user.id)
    await msg.answer(get_locale(data["lang"])["cabinet"], reply_markup=cabinet_kb(data["lang"]))

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    new_lang = cb.data.split(":")[1]
    await db_exec(
        "INSERT INTO accounts (user_id, lang_code) VALUES (%s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET lang_code = EXCLUDED.lang_code",
        (cb.from_user.id, new_lang)
    )
    L = get_locale(new_lang)
    await cb.message.edit_text(L["lang_changed"], reply_markup=cabinet_kb(new_lang))
    await cb.answer()
