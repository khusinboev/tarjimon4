# src/handlers/users/vocabs.py
import asyncio
import random
import math
from typing import List, Dict, Any
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
        "main_menu": "🏠 Bosh menyu"
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
        "main_menu": "🏠 Main menu"
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
    row = await db_exec(
        "SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (user_id,), fetch=True
    )
    return row["lang_code"] if row and row.get("lang_code") else "uz"

async def set_user_lang(user_id: int, lang: str):
    row = await db_exec(
        "SELECT id FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1",
        (user_id,), fetch=True
    )
    if row:
        await db_exec("UPDATE accounts SET lang_code=%s WHERE id=%s", (lang, row["id"]))
    else:
        await db_exec("INSERT INTO accounts (user_id, lang_code) VALUES (%s,%s)", (user_id, lang))

# -------------------- FSM --------------------

class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# -------------------- Pagination helpers --------------------

PAGE_SIZE = 6

def paginate_buttons(rows: List[Dict[str, Any]], page: int, lang: str, prefix: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    total = len(rows)
    total_pages = math.ceil(total / PAGE_SIZE)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    subset = rows[start:end]

    buttons = []
    row = []
    for i, r in enumerate(subset, start=1):
        row.append(InlineKeyboardButton(text=r["name"], callback_data=f"{prefix}:open:{r['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("⬅️", callback_data=f"{prefix}:page:{page-1}"))
        nav.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("➡️", callback_data=f"{prefix}:page:{page+1}"))
        buttons.append(nav)

    buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- Cabinet --------------------

@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    lang = await get_user_lang(msg.from_user.id)
    L = LOCALES[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")],
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])
    await msg.answer(L["cabinet"], reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("cab:"))
async def cb_cabinet(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    if cb.data == "cab:settings":
        await cb.message.edit_text(L["choose_lang"], reply_markup=settings_kb(lang))
    elif cb.data == "cab:back":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
            [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")],
            [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
        ])
        await cb.message.edit_text(L["cabinet"], reply_markup=kb)
    elif cb.data == "cab:new":
        await cb.message.edit_text(L["enter_book_name"], reply_markup=back_to_cabinet_kb(lang))
        await state.set_state(VocabStates.waiting_book_name)
    elif cb.data == "cab:books":
        rows = await db_exec(
            "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,), fetch=True, many=True
        )
        if not rows:
            await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
            return
        await cb.message.edit_text(L["my_books"], reply_markup=paginate_buttons(rows, 0, lang, "book"))
    elif cb.data == "cab:practice":
        rows = await db_exec(
            "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,), fetch=True, many=True
        )
        if not rows:
            await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
            return
        await cb.message.edit_text(L["practice"], reply_markup=paginate_buttons(rows, 0, lang, "practice"))

# -------------------- Pagination handler --------------------

@router.callback_query(lambda c: c.data and (c.data.startswith("book:page:") or c.data.startswith("practice:page:")))
async def cb_books_page(cb: CallbackQuery):
    parts = cb.data.split(":")
    prefix = parts[0]
    page = int(parts[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    rows = await db_exec(
        "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,), fetch=True, many=True
    )
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return

    title = L["my_books"] if prefix == "book" else L["practice"]
    await cb.message.edit_text(title, reply_markup=paginate_buttons(rows, page, lang, prefix))



# -------------------- Settings KB --------------------

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="setlang:uz")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en")],
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")],
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])

def back_to_cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

# -------------------- Settings handler --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("setlang:"))
async def cb_set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = LOCALES[lang]
    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))

# -------------------- Create book --------------------

@router.message(VocabStates.waiting_book_name)
async def msg_new_book_name(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    name = msg.text.strip()

    row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s",
                        (user_id, name), fetch=True)
    if row:
        await msg.answer(L["book_exists"], reply_markup=cabinet_kb(lang))
        await state.clear()
        return

    await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s)",
                  (user_id, name))
    row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s ORDER BY id DESC LIMIT 1",
                        (user_id, name), fetch=True)

    await msg.answer(L["book_created"].format(name=name, id=row["id"]),
                     reply_markup=cabinet_kb(lang))
    await state.clear()

# -------------------- Add words --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:open:"))
async def cb_book_open(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete:{book_id}")],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:books")]
    ])
    await cb.message.edit_text(f"📖 {L['my_books']} (id={book_id})", reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    await state.update_data(book_id=book_id)
    await cb.message.edit_text(L["send_pairs"], reply_markup=back_to_cabinet_kb(lang))
    await state.set_state(VocabStates.waiting_word_list)

@router.message(VocabStates.waiting_word_list)
async def msg_add_pairs(msg: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    lines = msg.text.strip().splitlines()
    pairs = []
    for line in lines:
        if "-" in line:
            w, t = line.split("-", 1)
            pairs.append((w.strip(), t.strip()))
    if not pairs:
        await msg.answer("❌ Format noto‘g‘ri.")
        return

    for w, t in pairs:
        await db_exec("INSERT INTO vocab_words (book_id, word, translation) VALUES (%s,%s,%s)",
                      (book_id, w, t))

    await msg.answer(L["added_pairs"].format(n=len(pairs)),
                     reply_markup=back_to_cabinet_kb(lang))

# -------------------- Delete book --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete:"))
async def cb_book_delete(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"book:del_yes:{book_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")]
    ])
    await cb.message.edit_text(L["confirm_delete"], reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("book:del_yes:"))
async def cb_book_del_yes(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    await db_exec("DELETE FROM vocab_words WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))
    await cb.message.edit_text("✅ O‘chirildi", reply_markup=cabinet_kb(lang))

# -------------------- Practice --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("practice:open:"))
async def cb_practice_open(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    words = await db_exec("SELECT id, word, translation FROM vocab_words WHERE book_id=%s",
                          (book_id,), fetch=True, many=True)
    if not words:
        await cb.message.edit_text(L["empty_book"], reply_markup=cabinet_kb(lang))
        return

    random.shuffle(words)
    await state.update_data(book_id=book_id, words=words, correct=0, wrong=0, index=0)
    await state.set_state(VocabStates.practicing)

    word = words[0]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=w["translation"], callback_data=f"ans:{w['id']}")]
        for w in random.sample(words, min(4, len(words)))
    ])
    await cb.message.edit_text(L["question"].format(word=word["word"]), reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    words = data.get("words", [])
    index = data.get("index", 0)
    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    if index >= len(words):
        await cb.message.edit_text(L["session_end"], reply_markup=cabinet_kb(lang))
        await state.clear()
        return

    current = words[index]
    chosen_id = int(cb.data.split(":")[1])
    if chosen_id == current["id"]:
        correct += 1
        await cb.answer(L["correct"], show_alert=False)
    else:
        wrong += 1
        await cb.answer(L["wrong"].format(correct=current["translation"]), show_alert=True)

    index += 1
    if index >= len(words):
        await cb.message.edit_text(
            L["results"].format(total=len(words), correct=correct, wrong=wrong),
            reply_markup=cabinet_kb(lang)
        )
        await state.clear()
        return

    next_word = words[index]
    opts = random.sample(words, min(4, len(words)))
    if next_word not in opts:
        opts[0] = next_word
    random.shuffle(opts)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=w["translation"], callback_data=f"ans:{w['id']}")]
        for w in opts
    ])

    await state.update_data(words=words, index=index, correct=correct, wrong=wrong)
    await cb.message.edit_text(L["question"].format(word=next_word["word"]), reply_markup=kb)
