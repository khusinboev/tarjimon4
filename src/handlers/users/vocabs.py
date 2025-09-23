# src/handlers/users/vocabs.py

import asyncio
import random
from typing import List, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import db

router = Router()

# =====================================================
# 📌 Localization
# =====================================================

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
        "main_menu": "🏠 Main menu"
    }
}

# =====================================================
# 📌 Database helpers
# =====================================================

async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False):
    """Universal DB executor"""
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

# =====================================================
# 📌 FSM States
# =====================================================

class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# =====================================================
# 📌 UI Builders
# =====================================================

def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    # As requested: show Practice prominently, My books and Settings below
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books"),
         InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")
        ],
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    # Removed 'practice' from book menu as requested
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete_confirm:{book_id}")],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:books")]
    ])

def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"book:delete_yes:{book_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")]
    ])

def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data=f"book:open:{book_id}")]
    ])

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["main_menu"], callback_data="cab:back")]
    ])

def back_to_cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

# =====================================================
# 📌 Cabinet menu
# =====================================================

@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    """Show main cabinet menu"""
    lang = await get_user_lang(msg.from_user.id)
    L = LOCALES[lang]
    await msg.answer(L["cabinet"], reply_markup=cabinet_kb(lang))


@router.callback_query(lambda c: c.data and c.data.startswith("cab:"))
async def cb_cabinet(cb: CallbackQuery, state: FSMContext):
    """Handle cabinet menu buttons"""
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    if cb.data == "cab:settings":
        await cb.message.edit_text(L["choose_lang"], reply_markup=settings_kb(lang))

    elif cb.data == "cab:back":
        await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))

    elif cb.data == "cab:new":
        await cb.message.edit_text(L["enter_book_name"], reply_markup=back_to_cabinet_kb(lang))
        await state.set_state(VocabStates.waiting_book_name)

    elif cb.data == "cab:books":
        rows = await db_exec(
            "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,), fetch=True, many=True
        )

        # 🔑 If no books -> alert
        if not rows:
            await cb.answer(L["no_books"], show_alert=True)
            return

        # Buttons: only open book (no practice in book menu)
        buttons = [
            [InlineKeyboardButton(text=r["name"], callback_data=f"book:open:{r['id']}")]
            for r in rows
        ]
        buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

        await cb.message.edit_text(
            L["my_books"],
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

    elif cb.data == "cab:practice":
        # Show list of books to choose from for practice
        rows = await db_exec(
            "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
            (user_id,), fetch=True, many=True
        )
        if not rows:
            await cb.answer(L["no_books"], show_alert=True)
            return

        buttons = [
            [InlineKeyboardButton(text=r["name"], callback_data=f"book:practice:{r['id']}")]
            for r in rows
        ]
        buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

        try:
            await cb.message.edit_text("📚 " + L["practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
        except Exception:
            await cb.message.answer("📚 " + L["practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    """Change user language"""
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = LOCALES[lang]

    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))
    await cb.answer("Language changed ✅")

# =====================================================
# 📌 Books management
# =====================================================

@router.message(VocabStates.waiting_book_name)
async def add_book(msg: Message, state: FSMContext):
    """Add a new book"""
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    name = msg.text.strip()
    row = await db_exec(
        "SELECT id FROM vocab_books WHERE user_id=%s AND name=%s",
        (user_id, name), fetch=True
    )
    if row:
        await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    row = await db_exec(
        "INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id",
        (user_id, name), fetch=True
    )
    await msg.answer(L["book_created"].format(name=name, id=row["id"]), reply_markup=main_menu_kb(lang))
    await state.clear()


@router.callback_query(lambda c: c.data and c.data.startswith("book:open:"))
async def cb_book_open(cb: CallbackQuery):
    """Open specific book menu"""
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)

    try:
        await cb.message.edit_text(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang))
    except Exception:
        await cb.message.answer(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang))

# -------- Delete book --------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_confirm:"))
async def cb_book_delete_confirm(cb: CallbackQuery):
    """Ask confirmation before deleting a book"""
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    await cb.message.edit_text(L["confirm_delete"], reply_markup=confirm_delete_kb(book_id, lang))


@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_yes:"))
async def cb_book_delete(cb: CallbackQuery):
    """Delete book and its words"""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))

    rows = await db_exec(
        "SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
        (user_id,), fetch=True, many=True
    )
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return

    buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:open:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

    await cb.message.edit_text(L["my_books"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

# -------- Add words --------

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    """Switch to adding words mode"""
    book_id = int(cb.data.split(":")[2])
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    try:
        await cb.message.edit_text(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))
    except Exception:
        await cb.message.answer(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))

    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)


@router.message(VocabStates.waiting_word_list)
async def add_words(msg: Message, state: FSMContext):
    """Add word pairs into a book"""
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
        await msg.answer("❌ Xato format.", reply_markup=add_words_back_kb(book_id, lang))
        return

    for w, t in pairs:
        await db_exec(
            "INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (book_id, w, t)
        )

    await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))

# -------- Practice --------

@router.callback_query(lambda c: c.data and c.data.startswith("book:practice:"))
async def cb_book_practice(cb: CallbackQuery, state: FSMContext):
    """Start practice session if enough words"""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    # Get book words
    rows = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s",
        (book_id,), fetch=True, many=True
    )

    if not rows or len(rows) < 4:
        await cb.answer("❌ " + L["empty_book"], show_alert=True)
        return

    # Prepare and shuffle
    random.shuffle(rows)

    # Initialize richer stats:
    await state.update_data(
        book_id=book_id,
        words=rows,
        index=0,
        correct=0,
        wrong=0,
        total=len(rows),
        answers=0,              # total answered questions
        cycles=0,               # completed full cycles
        current_cycle_correct=0,
        current_cycle_wrong=0,
        cycles_stats=[]         # list of dicts {correct, wrong} per completed cycle
    )
    await state.set_state(VocabStates.practicing)

    await send_next_question(cb.message, state, lang)


async def send_next_question(msg: Message, state: FSMContext, lang: str):
    """Helper: send next practice question (goes in cycle; when reaches end, count cycle and reshuffle)"""
    data = await state.get_data()
    words = data["words"]
    index = data["index"]
    L = LOCALES[lang]

    # If reached end -> complete a cycle
    if index >= len(words):
        # store cycle stats
        cycles = data.get("cycles", 0) + 1
        c_corr = data.get("current_cycle_correct", 0)
        c_wrong = data.get("current_cycle_wrong", 0)
        cycles_stats = data.get("cycles_stats", [])
        cycles_stats.append({"correct": c_corr, "wrong": c_wrong})

        # reset per-cycle counters and reshuffle
        random.shuffle(words)
        await state.update_data(
            words=words,
            index=0,
            cycles=cycles,
            current_cycle_correct=0,
            current_cycle_wrong=0,
            cycles_stats=cycles_stats
        )
        index = 0
        data = await state.get_data()

    current = data["words"][index]
    correct_answer = current["word_trg"]

    # Prepare options
    options = [correct_answer]
    while len(options) < 4 and len(options) < len(data["words"]):
        candidate = random.choice(data["words"])["word_trg"]
        if candidate not in options:
            options.append(candidate)
    random.shuffle(options)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=o, callback_data=f"ans:{index}:{o}")]
        for o in options
    ] + [
        [InlineKeyboardButton(text=L["finish"], callback_data="practice:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])

    # Use edit_text when possible, else send new
    try:
        await msg.edit_text(L["question"].format(word=current["word_src"]),
                            reply_markup=keyboard)
    except Exception:
        await msg.answer(L["question"].format(word=current["word_src"]), reply_markup=keyboard)


@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    """Check practice answer and update enhanced stats"""
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()
    words = data["words"]
    index = data["index"]

    _, idx, chosen = cb.data.split(":", 2)
    idx = int(idx)
    # Protect against index out of range (race)
    if idx < 0 or idx >= len(words):
        await cb.answer("❌", show_alert=True)
        return

    current = words[idx]
    correct_answer = current["word_trg"]

    # Update totals
    data.setdefault("answers", 0)
    data["answers"] += 1

    if chosen == correct_answer:
        data["correct"] = data.get("correct", 0) + 1
        data["current_cycle_correct"] = data.get("current_cycle_correct", 0) + 1
        await cb.answer(L["correct"])
    else:
        data["wrong"] = data.get("wrong", 0) + 1
        data["current_cycle_wrong"] = data.get("current_cycle_wrong", 0) + 1
        await cb.answer(L["wrong"].format(correct=correct_answer), show_alert=True)

    # Move forward
    data["index"] = index + 1
    await state.update_data(**data)

    # Send next
    await send_next_question(cb.message, state, lang)


@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    """Finish practice session and show localized simple stats"""
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()

    total_unique = data.get("total", 0)       # Savollar soni
    total_answers = data.get("answers", 0)    # Berilgan jami savollar
    total_correct = data.get("correct", 0)    # To‘g‘ri javoblar
    total_wrong = data.get("wrong", 0)        # Xato javoblar

    percent = (total_correct / total_answers * 100) if total_answers > 0 else 0.0

    full_text = (
        f"{L['results_header']}\n\n" +
        L['results_lines'].format(
            unique=total_unique,
            answers=total_answers,
            correct=total_correct,
            wrong=total_wrong,
            percent=percent
        )
    )

    await state.clear()

    try:
        await cb.message.edit_text(full_text)
    except Exception:
        await cb.message.answer(full_text)

    # Show cabinet menu after results
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(lang))