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
# 📌 Localization (unchanged, as it's already compact)
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
    }
}

# =====================================================
# 📌 Database helpers (optimized: combined lang fetch)
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
# 📌 FSM States (unchanged)
# =====================================================
class VocabStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()
    practicing = State()

# =====================================================
# 📌 UI Builders (optimized: reuse L, fix two-col for odd counts)
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
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books"),
         InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
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

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["export"], callback_data=f"book:export:{book_id}")],
        [InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete_confirm:{book_id}")],
        [InlineKeyboardButton(text=L["back"], callback_data="cab:books")]
    ])

def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"book:delete_yes:{book_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")]
    ])

def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_locale(lang)["back_to_book"], callback_data=f"book:open:{book_id}")]
    ])

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=get_locale(lang)["main_menu"], callback_data="cab:back")]
    ])

def new_book_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["cancel"], callback_data="cab:back")]
    ])

def books_kb(books: List[Dict], lang: str, for_practice: bool = False) -> InlineKeyboardMarkup:
    """Unified KB builder for books list."""
    L = get_locale(lang)
    btns = []
    for b in books:
        action = f"book:practice:{b['id']}" if for_practice else f"book:open:{b['id']}"
        btns.append(InlineKeyboardButton(text=b["name"], callback_data=action))
    btns.extend([
        # InlineKeyboardButton(text=L["new_book"], callback_data="cab:new"),
        InlineKeyboardButton(text=L["back"], callback_data="cab:back")
    ])
    return InlineKeyboardMarkup(inline_keyboard=two_col_rows(btns))

# =====================================================
# 📌 Export helper (optimized: check rows early)
# =====================================================
async def export_book_to_excel(book_id: int, user_id: int) -> str:
    rows = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id",
        (book_id,), fetch=True, many=True
    )
    if len(rows) < 1:  # At least one row for export
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
# 📌 Helper to send message (always delete old if edit fails)
# =====================================================
async def safe_edit_or_send(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup, lang: str):
    """Delete old message and send new to avoid edit issues with old inlines."""
    try:
        await cb.message.delete()
    except:
        pass
    await cb.message.answer(text, reply_markup=kb)

# =====================================================
# 📌 Cabinet menu (optimized: batch fetch)
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
    lang, books = data["lang"], data["books"]
    L = get_locale(lang)

    if cb.data == "cab:settings":
        await safe_edit_or_send(cb, L["choose_lang"], settings_kb(lang), lang)

    elif cb.data == "cab:back":
        await safe_edit_or_send(cb, L["cabinet"], cabinet_kb(lang), lang)

    elif cb.data == "cab:new":
        await safe_edit_or_send(cb, L["enter_book_name"], new_book_cancel_kb(lang), lang)
        await state.set_state(VocabStates.waiting_book_name)

    elif cb.data == "cab:books":
        if not books:
            kb = InlineKeyboardMarkup(inline_keyboard=two_col_rows([
                InlineKeyboardButton(text=L["new_book"], callback_data="cab:new"),
                InlineKeyboardButton(text=L["back"], callback_data="cab:back")
            ]))
            await safe_edit_or_send(cb, L["my_books"], kb, lang)
            return
        await safe_edit_or_send(cb, L["my_books"], books_kb(books, lang), lang)

    elif cb.data == "cab:practice":
        if not books:
            await cb.answer(L["no_books"], show_alert=True)
            return
        await safe_edit_or_send(cb, "📚 " + L["practice"], books_kb(books, lang, for_practice=True), lang)
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

# =====================================================
# 📌 Books management (optimized: reuse data fetch)
# =====================================================

@router.message(VocabStates.waiting_book_name)
async def add_book(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    name = msg.text.strip()
    if await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True):
        await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
    book_id = row["id"] if row else None
    await msg.answer(L["book_created"].format(name=name, id=book_id), reply_markup=main_menu_kb(lang))
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:open:"))
async def cb_book_open(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    await safe_edit_or_send(cb, f"📖 Book {book_id}", book_kb(book_id, lang), lang)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_confirm:"))
async def cb_book_delete_confirm(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)
    await safe_edit_or_send(cb, L["confirm_delete"], confirm_delete_kb(book_id, lang), lang)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_yes:"))
async def cb_book_delete(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))

    data = await get_user_data(user_id)
    lang, books = data["lang"], data["books"]
    L = get_locale(lang)
    if not books:
        await safe_edit_or_send(cb, L["no_books"], cabinet_kb(lang), lang)
        return
    await safe_edit_or_send(cb, L["my_books"], books_kb(books, lang), lang)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)
    await safe_edit_or_send(cb, L["send_pairs"], add_words_back_kb(book_id, lang), lang)
    await state.update_data(book_id=book_id)
    await state.set_state(VocabStates.waiting_word_list)
    await cb.answer()

@router.message(VocabStates.waiting_word_list)
async def add_words(msg: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data["book_id"]
    user_data = await get_user_data(msg.from_user.id)
    lang = user_data["lang"]
    L = get_locale(lang)

    lines = msg.text.strip().split("\n")
    pairs = [(w.strip(), t.strip()) for line in lines if "-" in line for w, t in [line.split("-", 1)]]

    if not pairs:
        await msg.answer("❌ Xato format.", reply_markup=add_words_back_kb(book_id, lang))
        return

    for w, t in pairs:
        await db_exec("INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (book_id, w, t))

    await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:export:"))
async def cb_book_export(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    await cb.answer("⏳ Fayl tayyorlanmoqda...")
    file_path = await export_book_to_excel(book_id, user_id)
    if not file_path:
        await cb.answer("❌ " + L["empty_book"], show_alert=True)
        return

    try:
        await cb.message.delete()
        file = FSInputFile(file_path)
        await cb.message.answer_document(file, caption="📤 " + L["export"])
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    # Refresh and send books list
    refreshed_data = await get_user_data(user_id)
    if not refreshed_data["books"]:
        await cb.message.answer(L["no_books"], reply_markup=cabinet_kb(lang))
    else:
        await cb.message.answer(L["my_books"], reply_markup=books_kb(refreshed_data["books"], lang))
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:practice:"))
async def cb_book_practice(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s", (book_id,), fetch=True, many=True)

    if len(rows) < 4:
        data = await get_user_data(cb.from_user.id)
        await cb.answer("❌ " + get_locale(data["lang"])["empty_book"], show_alert=True)
        return

    random.shuffle(rows)
    await state.update_data(
        book_id=book_id, words=rows, index=0, correct=0, wrong=0, total=len(rows),
        answers=0, cycles=0, current_cycle_correct=0, current_cycle_wrong=0, cycles_stats=[]
    )
    await state.set_state(VocabStates.practicing)
    data = await get_user_data(cb.from_user.id)
    await send_next_question(cb.message, state, data["lang"])
    await cb.answer()

async def send_next_question(msg: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    words, index = data["words"], data["index"]
    L = get_locale(lang)

    if index >= len(words):
        cycles = data.get("cycles", 0) + 1
        cycles_stats = data.get("cycles_stats", [])
        cycles_stats.append({
            "correct": data.get("current_cycle_correct", 0),
            "wrong": data.get("current_cycle_wrong", 0)
        })
        random.shuffle(words)
        await state.update_data(
            words=words, index=0, cycles=cycles, cycles_stats=cycles_stats,
            current_cycle_correct=0, current_cycle_wrong=0
        )
        data = await state.get_data()
        index = 0

    current = data["words"][index]
    correct_answer = current["word_trg"]
    options = [correct_answer]
    seen = set(options)
    while len(options) < 4 and len(options) < len(data["words"]):
        candidate = random.choice(data["words"])["word_trg"]
        if candidate not in seen:
            options.append(candidate)
            seen.add(candidate)
    random.shuffle(options)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=o, callback_data=f"ans:{index}:{o}")] for o in options
    ] + [
        [InlineKeyboardButton(text=L["finish"], callback_data="practice:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])

    await msg.edit_text(L["question"].format(word=current["word_src"]), reply_markup=kb)  # Practice messages are fresh, so edit ok

@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    _, idx_str, chosen = cb.data.split(":", 2)
    idx = int(idx_str)
    if idx >= len(data["words"]):
        await cb.answer("❌", show_alert=True)
        return

    current = data["words"][idx]
    correct_answer = current["word_trg"]
    data["answers"] = data.get("answers", 0) + 1

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    if chosen == correct_answer:
        data["correct"] = data.get("correct", 0) + 1
        data["current_cycle_correct"] = data.get("current_cycle_correct", 0) + 1
        await cb.answer(L["correct"])
    else:
        data["wrong"] = data.get("wrong", 0) + 1
        data["current_cycle_wrong"] = data.get("current_cycle_wrong", 0) + 1
        await cb.answer(L["wrong"].format(correct=correct_answer), show_alert=True)

    data["index"] = idx + 1
    await state.update_data(**data)
    await send_next_question(cb.message, state, user_data["lang"])

@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total_unique, total_answers = data.get("total", 0), data.get("answers", 0)
    total_correct, total_wrong = data.get("correct", 0), data.get("wrong", 0)
    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])
    full_text = f"{L['results_header']}\n\n{L['results_lines'].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)}"

    await state.clear()
    await cb.message.edit_text(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()