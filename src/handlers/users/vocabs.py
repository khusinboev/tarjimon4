# src/handlers/users/vocabs.py
import asyncio
import json
import random
from typing import List, Dict, Any, Optional
from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import db

router = Router()

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
        "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}",
        "no_books": "Sizda hali lug'at yo'q.",
        "enter_book_name": "Yangi lug'at nomini kiriting:",
        "book_created": "✅ Lug'at yaratildi: {name} (id={id})",
        "book_exists": "❌ Bu nom bilan lug'at mavjud.",
        "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).",
        "added_pairs": "✅ {n} ta juftlik qo'shildi.",
        "empty_book": "❌ Bu lug'at bo'sh.",
        "question": "❓ {word}",
        "correct": "✅ To'g'ri",
        "wrong": "❌ Xato. To‘g‘ri javob: {correct}",
        "finish": "🏁 Tugatish",
        "session_end": "Mashq tugadi."
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
        "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}",
        "no_books": "You have no books yet.",
        "enter_book_name": "Enter new book name:",
        "book_created": "✅ Book created: {name} (id={id})",
        "book_exists": "❌ Book with this name already exists.",
        "send_pairs": "Send word pairs (each line: word-translation).",
        "added_pairs": "✅ {n} pairs added.",
        "empty_book": "❌ This book is empty.",
        "question": "❓ {word}",
        "correct": "✅ Correct",
        "wrong": "❌ Wrong. Correct: {correct}",
        "finish": "🏁 Finish",
        "session_end": "Practice finished."
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
    # Avval foydalanuvchi mavjudmi?
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

# -------------------- UI builders --------------------
def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")],
        [InlineKeyboardButton(text=L["new_book"], callback_data="cab:new")],
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data=f"book:practice:{book_id}")],
        [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:books")]
    ])

# -------------------- Cabinet --------------------
@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    lang = await get_user_lang(msg.from_user.id)
    L = LOCALES[lang]
    await msg.answer(L["cabinet"], reply_markup=cabinet_kb(lang))

@router.callback_query(lambda c: c.data and c.data.startswith("cab:"))
async def cb_cabinet(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    if cb.data == "cab:settings":
        await cb.message.edit_text(L["choose_lang"], reply_markup=settings_kb(lang))

    elif cb.data == "cab:back":
        await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))

    elif cb.data == "cab:new":
        await cb.message.edit_text(L["enter_book_name"])
        await state.set_state(VocabStates.waiting_book_name)

    elif cb.data == "cab:books":
        rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
        if not rows:
            await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
            return
        buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:open:{r['id']}")] for r in rows]
        buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
        await cb.message.edit_text(L["my_books"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = LOCALES[lang]
    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))
    await cb.answer("Language changed ✅")

# -------------------- Books --------------------
@router.message(VocabStates.waiting_book_name)
async def add_book(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    name = msg.text.strip()
    row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
    if row:
        await msg.answer(L["book_exists"])
        await state.clear()
        return

    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
    await msg.answer(L["book_created"].format(name=name, id=row["id"]), reply_markup=cabinet_kb(lang))
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:open:"))
async def cb_book_open(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    await cb.message.edit_text(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    await cb.message.edit_text(L["send_pairs"])
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)

@router.message(VocabStates.waiting_word_list)
async def add_words(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()
    book_id = data["book_id"]

    lines = msg.text.strip().split("\n")
    pairs = []
    for line in lines:
        if "-" in line:
            w, t = line.split("-", 1)
            pairs.append((w.strip(), t.strip()))
    if not pairs:
        await msg.answer("❌ Xato format.")
        return

    for w, t in pairs:
        await db_exec("INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (book_id, w, t))

    await msg.answer(L["added_pairs"].format(n=len(pairs)))
    await state.clear()

# -------------------- Practice --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("book:practice:"))
async def cb_book_practice(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    words = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s AND is_active=TRUE", (book_id,), fetch=True, many=True)
    if not words:
        await cb.message.edit_text(L["empty_book"], reply_markup=book_kb(book_id, lang))
        return

    await state.set_state(VocabStates.practicing)
    await state.update_data(book_id=book_id, words=words)

    await ask_question(cb.message, words, lang)


async def ask_question(msg: Message, words: List[Dict[str, Any]], lang: str):
    """Savol yuborish: random tanlov, random til yo‘nalishi"""
    L = LOCALES[lang]
    entry = random.choice(words)
    ask_src = random.choice([True, False])  # qaysi tildan so‘raladi

    presented = entry["word_src"] if ask_src else entry["word_trg"]
    correct = entry["word_trg"] if ask_src else entry["word_src"]

    # Distraktorlarni tanlash
    if ask_src:
        pool = [w["word_trg"] for w in words if w["id"] != entry["id"]]
    else:
        pool = [w["word_src"] for w in words if w["id"] != entry["id"]]

    wrongs = random.sample(pool, min(3, len(pool)))
    options = wrongs + [correct]
    random.shuffle(options)

    # Tugmalarni 2 ustunda joylashtirish
    buttons = []
    row = []
    for i, opt in enumerate(options, start=1):
        row.append(InlineKeyboardButton(text=opt, callback_data=f"ans:{entry['id']}:{opt}:{correct}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Tugatish tugmasi
    buttons.append([InlineKeyboardButton(text=L["finish"], callback_data="practice:finish")])

    await msg.edit_text(L["question"].format(word=presented), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_answer(cb: CallbackQuery, state: FSMContext):
    # data: ans:{entry_id}:{chosen}:{correct}
    _, eid, chosen, correct = cb.data.split(":", 3)

    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    if chosen == correct:
        await cb.answer(L["correct"])
    else:
        await cb.answer(L["wrong"].format(correct=correct))

    data = await state.get_data()
    words = data["words"]

    # Keyingi savolni darhol chiqaramiz (cheksiz aylanish)
    await ask_question(cb.message, words, lang)


@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_finish(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    await cb.message.edit_text(L["session_end"])
    await state.clear()