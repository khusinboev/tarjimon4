# src/handlers/users/vocabs.py
import asyncio
import random
import io
import csv
from typing import List, Dict, Any, Optional, Tuple

from aiogram import Router
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputFile
)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import db

router = Router()

# -------------------- Config --------------------
BOOKS_PER_PAGE = 8  # pagination size

# -------------------- Localization --------------------
LOCALES = {
    "uz": {
        "cabinet": "📚 Kabinet",
        "choose_lang": "Tilni tanlang:",
        "my_books": "📖 Mening lug'atlarim",
        "new_book": "➕ Yangi lug'at",
        "settings": "⚙️ Sozlamalar",
        "back": "🔙 Orqaga",
        "practice": "▶ Mashq",
        "add_words": "➕ So'z qo'shish",
        "delete": "❌ O‘chirish",
        "confirm_delete": "❓ Ushbu lug‘atni o‘chirishga ishonchingiz komilmi?",
        "yes": "✅ Ha",
        "no": "❌ Yo‘q",
        "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}",
        "no_books": "Sizda hali lug'at yo'q.",
        "enter_book_name": "Yangi lug'at nomini kiriting:",
        "book_created": "✅ Lug'at yaratildi: {name} (id={id})",
        "book_exists": "❌ Bu nom bilan lug'at mavjud.",
        "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).",
        "added_pairs": "✅ {n} ta juftlik qo'shildi. Yana yuborishingiz mumkin 👇",
        "empty_book": "❌ Bu lug'at bo'sh.",
        "question": "❓ {word}",
        "correct": "✅ To'g'ri",
        "wrong": "❌ Xato. To‘g‘ri javob: {correct}",
        "finish": "🏁 Tugatish",
        "session_end": "Mashq tugadi.",
        "back_to_book": "🔙 Orqaga",
        "main_menu": "🏠 Bosh menyu",
        "choose_book_practice": "Mashq uchun lug'atni tanlang:",
        "created_ask_add": "Lug'at yaratildi. Hozir so'zlar qo'shasizmi?",
        "add_now": "➕ Ha, hozir qo'shaman",
        "add_later": "🔙 Orqaga",
        "export_excel": "📥 Excelga yuklab olish",
        "delete_entry": "🗑️ Juftlikni o'chirish",
        "export_success": "✅ Eksport tayyorlandi.",
        "no_entries": "Bu lug'atda so'zlar mavjud emas.",
        "entry_deleted": "✅ Juftlik o'chirildi.",
        "book_deleted": "✅ Lug'at o'chirildi.",
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
        "confirm_delete": "❓ Are you sure you want to delete this book?",
        "yes": "✅ Yes",
        "no": "❌ No",
        "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}",
        "no_books": "You have no books yet.",
        "enter_book_name": "Enter new book name:",
        "book_created": "✅ Book created: {name} (id={id})",
        "book_exists": "❌ Book with this name already exists.",
        "send_pairs": "Send word pairs (each line: word-translation).",
        "added_pairs": "✅ {n} pairs added. You can send more 👇",
        "empty_book": "❌ This book is empty.",
        "question": "❓ {word}",
        "correct": "✅ Correct",
        "wrong": "❌ Wrong. Correct: {correct}",
        "finish": "🏁 Finish",
        "session_end": "Practice finished.",
        "back_to_book": "🔙 Back",
        "main_menu": "🏠 Main menu",
        "choose_book_practice": "Choose a book for practice:",
        "created_ask_add": "Book created. Add words now?",
        "add_now": "➕ Yes, add now",
        "add_later": "🔙 Back",
        "export_excel": "📥 Export to Excel",
        "delete_entry": "🗑️ Delete pair",
        "export_success": "✅ Export ready.",
        "no_entries": "This book has no entries.",
        "entry_deleted": "✅ Pair deleted.",
        "book_deleted": "✅ Book deleted.",
    }
}

# -------------------- DB helpers --------------------
async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False):
    def run():
        cur = db.cursor()
        cur.execute(query, params or ())
        if fetch:
            if many:
                rows = cur.fetchall()
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

async def get_user_lang(user_id: int) -> str:
    row = await db_exec("SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True)
    return row["lang_code"] if row and row.get("lang_code") else "uz"

async def set_user_lang(user_id: int, lang: str):
    row = await db_exec("SELECT id FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True)
    if row:
        await db_exec("UPDATE accounts SET lang_code=%s WHERE id=%s", (lang, row["id"]))
    else:
        await db_exec("INSERT INTO accounts (user_id, lang_code) VALUES (%s,%s)", (user_id, lang))

# -------------------- FSM --------------------
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()
    waiting_book_name_from_mybooks = State()  # separate state for new book from "My books"

# (shu joygacha sening kodinga o‘xshash)

# -------------------- Practice flow --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("book:practice:"))
async def cb_book_practice(cb: CallbackQuery, state: FSMContext):
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    words = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s", (book_id,), fetch=True, many=True)
    if not words:
        await cb.message.edit_text(L["empty_book"], reply_markup=book_kb(book_id, lang))
        return

    await state.set_state(VocabStates.practicing)
    await state.update_data(book_id=book_id, words=words, correct=0, wrong=0, asked=[])

    await send_next_question(cb.message, state, lang)


async def send_next_question(msg: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    words = data.get("words", [])
    asked = data.get("asked", [])

    remaining = [w for w in words if w["id"] not in asked]
    if not remaining:
        total = len(words)
        correct = data.get("correct", 0)
        wrong = data.get("wrong", 0)
        await msg.answer(LOCALES[lang]["results"].format(total=total, correct=correct, wrong=wrong),
                         reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    word = random.choice(remaining)
    asked.append(word["id"])
    await state.update_data(current_word=word, asked=asked)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["finish"], callback_data="practice:finish")]
    ])
    await msg.answer(LOCALES[lang]["question"].format(word=word["word_src"]), reply_markup=kb)


@router.message(VocabStates.practicing)
async def handle_answer(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()
    word = data.get("current_word")
    if not word:
        await msg.answer("❌ Error. Restart practice.", reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    if msg.text.strip().lower() == word["word_trg"].strip().lower():
        await msg.answer(L["correct"])
        await state.update_data(correct=data.get("correct", 0) + 1)
    else:
        await msg.answer(L["wrong"].format(correct=word["word_trg"]))
        await state.update_data(wrong=data.get("wrong", 0) + 1)

    await send_next_question(msg, state, lang)


@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    data = await state.get_data()
    total = len(data.get("words", []))
    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    await cb.message.edit_text(L["session_end"] + "\n" + L["results"].format(total=total, correct=correct, wrong=wrong),
                               reply_markup=main_menu_kb(lang))
    await state.clear()