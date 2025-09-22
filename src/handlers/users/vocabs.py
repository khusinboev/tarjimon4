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

# -------------------- UI builders --------------------
def cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")],
        [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")],
        [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")]
    ])

def settings_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"),
         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["main_menu"], callback_data="cab:back")]
    ])

def back_to_cabinet_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")]
    ])

def back_to_book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data=f"book:open:{book_id}")]
    ])

def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    # only back button while in "send pairs" mode (user can keep sending messages)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data=f"book:open:{book_id}")]
    ])

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["practice"], callback_data=f"book:practice:{book_id}")],
        [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=LOCALES[lang]["export_excel"], callback_data=f"book:export:{book_id}")],
        [InlineKeyboardButton(text=LOCALES[lang]["delete"], callback_data=f"book:delete_confirm:{book_id}")],
        [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data="cab:books")]
    ])

def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"book:delete_yes:{book_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")]
    ])

def books_list_kb(books: List[Dict[str, Any]], page: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    buttons = []
    for b in books:
        buttons.append([InlineKeyboardButton(text=b["name"], callback_data=f"book:open:{b['id']}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⏮ Oldingi", callback_data=f"books:list:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back"))
    # We'll add Next only when called from outside to know total pages; a caller can include next button
    nav_row.append(InlineKeyboardButton(text="Keyingi ⏭", callback_data=f"books:list:{page+1}"))
    buttons.append(nav_row)

    # Add 'new book' button on top or bottom:
    buttons.append([InlineKeyboardButton(text=L["new_book"], callback_data="books:new")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def books_list_kb_with_total(books: List[Dict[str, Any]], page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    L = LOCALES[lang]
    buttons = []
    for b in books:
        buttons.append([InlineKeyboardButton(text=b["name"], callback_data=f"book:open:{b['id']}")])

    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⏮ Oldingi", callback_data=f"books:list:{page-1}"))
    nav_row.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ⏭", callback_data=f"books:list:{page+1}"))
    buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text=L["new_book"], callback_data="books:new")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# -------------------- Helpers --------------------
def paginate(items: List[Any], page: int, per_page: int) -> Tuple[List[Any], int]:
    total = len(items)
    total_pages = max((total + per_page - 1) // per_page, 1)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    return items[start:end], total_pages

# -------------------- Cabinet --------------------
@router.message(Command("cabinet"))
async def cmd_cabinet(msg: Message):
    lang = await get_user_lang(msg.from_user.id)
    await msg.answer(LOCALES[lang]["cabinet"], reply_markup=cabinet_kb(lang))

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
        # defensive: redirect to books:new flow
        await cb.message.edit_text(L["enter_book_name"], reply_markup=back_to_cabinet_kb(lang))
        await state.set_state(VocabStates.waiting_book_name)
    elif cb.data == "cab:books":
        # go to My books (page 1)
        # We'll fetch books for user and show first page
        rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
        if not rows:
            await cb.message.edit_text(L["no_books"], reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=L["new_book"], callback_data="books:new")],[InlineKeyboardButton(text=L["back"], callback_data="cab:back")]]))
            return
        page = 1
        paged, total_pages = paginate(rows, page, BOOKS_PER_PAGE)
        kb = books_list_kb_with_total(paged, page, total_pages, lang)
        await cb.message.edit_text(L["my_books"], reply_markup=kb)
    elif cb.data == "cab:practice":
        # show list of books for practice
        rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
        if not rows:
            await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
            return
        buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:practice:{r['id']}")] for r in rows]
        buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
        await cb.message.edit_text(L["choose_book_practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(lambda c: c.data and c.data.startswith("lang:"))
async def cb_change_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    await set_user_lang(cb.from_user.id, lang)
    L = LOCALES[lang]
    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))
    await cb.answer("Language changed ✅")

# -------------------- Books list pagination & create --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("books:list:"))
async def cb_books_list_page(cb: CallbackQuery):
    try:
        page = int(cb.data.split(":")[2])
    except Exception:
        page = 1
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return

    paged, total_pages = paginate(rows, page, BOOKS_PER_PAGE)
    kb = books_list_kb_with_total(paged, page, total_pages, lang)
    await cb.message.edit_text(L["my_books"], reply_markup=kb)

@router.callback_query(lambda c: c.data == "books:new")
async def cb_books_new(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    await cb.message.edit_text(L["enter_book_name"], reply_markup=back_to_cabinet_kb(lang))
    await state.set_state(VocabStates.waiting_book_name_from_mybooks)

@router.message(lambda m: True, state=VocabStates.waiting_book_name_from_mybooks)
async def create_book_from_mybooks(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    name = msg.text.strip()
    # check exists
    row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
    if row:
        await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
        await state.clear()
        return
    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
    book_id = row["id"]
    # ask whether to add words now
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["add_now"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["add_later"], callback_data="cab:books")]
    ])
    await msg.answer(L["book_created"].format(name=name, id=book_id), reply_markup=kb)
    await state.clear()

@router.message(lambda m: True, state=VocabStates.waiting_book_name)
async def create_book_from_cabinet(msg: Message, state: FSMContext):
    # similar to above but triggered from /cabinet
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    name = msg.text.strip()
    row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
    if row:
        await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
        await state.clear()
        return
    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
    book_id = row["id"]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["add_now"], callback_data=f"book:add:{book_id}")],
        [InlineKeyboardButton(text=L["add_later"], callback_data="cab:back")]
    ])
    await msg.answer(L["book_created"].format(name=name, id=book_id), reply_markup=kb)
    await state.clear()

# -------------------- Book page & actions --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("book:open:"))
async def cb_book_open(cb: CallbackQuery):
    # show book main menu (entries management etc)
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid book id")
        return
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]
    # Try to get book name
    book = await db_exec("SELECT id, name FROM vocab_books WHERE id=%s", (book_id,), fetch=True)
    if not book:
        await cb.message.edit_text("❌ Book not found.", reply_markup=cabinet_kb(lang))
        return
    # Show book menu
    try:
        await cb.message.edit_text(f"📖 {book['name']}", reply_markup=book_kb(book_id, lang))
    except Exception:
        await cb.message.answer(f"📖 {book['name']}", reply_markup=book_kb(book_id, lang))

# Delete book confirm and deletion
@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_confirm:"))
async def cb_book_delete_confirm(cb: CallbackQuery):
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]
    await cb.message.edit_text(L["confirm_delete"], reply_markup=confirm_delete_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_yes:"))
async def cb_book_delete(cb: CallbackQuery):
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    # Remove entries and book (cascade should handle entries, but for safety)
    await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))
    # Show updated books list (page 1)
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return
    paged, total_pages = paginate(rows, 1, BOOKS_PER_PAGE)
    kb = books_list_kb_with_total(paged, 1, total_pages, lang)
    await cb.message.edit_text(L["book_deleted"], reply_markup=kb)

# -------------------- Export to Excel/CSV --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("book:export:"))
async def cb_book_export(cb: CallbackQuery):
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]
    # fetch entries
    rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id ASC", (book_id,), fetch=True, many=True)
    if not rows:
        await cb.answer(L["no_entries"])
        return

    # Try to use pandas for nicer Excel, otherwise fallback to CSV bytes
    try:
        import pandas as pd  # type: ignore
        df = pd.DataFrame(rows)
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="entries")
            writer.save()
        bio.seek(0)
        filename = f"book_{book_id}_entries.xlsx"
        await cb.message.answer_document(InputFile(bio, filename=filename))
    except Exception:
        # fallback CSV
        bio = io.StringIO()
        writer = csv.writer(bio)
        writer.writerow(["word_src", "word_trg"])
        for r in rows:
            writer.writerow([r["word_src"], r["word_trg"]])
        bio_bytes = io.BytesIO(bio.getvalue().encode("utf-8"))
        filename = f"book_{book_id}_entries.csv"
        await cb.message.answer_document(InputFile(bio_bytes, filename=filename))

    await cb.answer(L["export_success"])

# -------------------- Add words --------------------
@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
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
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    data = await state.get_data()
    book_id = data.get("book_id") or data.get("book_id")  # defensive

    if not book_id:
        await msg.answer("❌ Book id not found in state.", reply_markup=main_menu_kb(lang))
        await state.clear()
        return

    lines = [ln.strip() for ln in msg.text.strip().split("\n") if ln.strip()]
    pairs = []
    for line in lines:
        if "-" in line:
            w, t = line.split("-", 1)
            pairs.append((w.strip(), t.strip()))

    if not pairs:
        await msg.answer("❌ Xato format.", reply_markup=add_words_back_kb(book_id, lang))
        return

    for w, t in pairs:
        try:
            await db_exec(
                "INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                (book_id, w, t)
            )
        except Exception:
            # ignore individual insert errors, continue
            continue

    await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))
    # Do NOT clear state: user may add more; he/she can press the back button to return

# -------------------- Delete single entry --------------------
# For deleting entries we will present a list of entries with "delete" buttons
@router.callback_query(lambda c: c.data and c.data.startswith("book:entries:"))
async def cb_book_entries_list(cb: CallbackQuery):
    # pattern: book:entries:{book_id}
    try:
        book_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]

    rows = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id DESC", (book_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_entries"], reply_markup=book_kb(book_id, lang))
        return

    buttons = []
    # We'll show up to 10 entries with delete buttons
    for r in rows[:15]:
        text = f"{r['word_src']} — {r['word_trg']}"
        buttons.append([InlineKeyboardButton(text=text, callback_data=f"entry:delete_confirm:{r['id']}")])
    buttons.append([InlineKeyboardButton(text=L["back_to_book"], callback_data=f"book:open:{book_id}")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await cb.message.edit_text("Select pair to delete:", reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("entry:delete_confirm:"))
async def cb_entry_delete_confirm(cb: CallbackQuery):
    try:
        entry_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    # fetch entry to get book_id and show confirm
    entry = await db_exec("SELECT id, book_id, word_src, word_trg FROM vocab_entries WHERE id=%s", (entry_id,), fetch=True)
    if not entry:
        await cb.answer("Entry not found")
        return
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"entry:delete_yes:{entry_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{entry['book_id']}")]
    ])
    await cb.message.edit_text(f"❓ {entry['word_src']} — {entry['word_trg']}\n{L['confirm_delete']}", reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("entry:delete_yes:"))
async def cb_entry_delete(cb: CallbackQuery):
    try:
        entry_id = int(cb.data.split(":")[2])
    except Exception:
        await cb.answer("Invalid id")
        return
    entry = await db_exec("SELECT id, book_id FROM vocab_entries WHERE id=%s", (entry_id,), fetch=True)
    if not entry:
        await cb.answer("Entry not found")
        return
    await db_exec("DELETE FROM vocab_entries WHERE id=%s", (entry_id,))
    lang = await get_user_lang(cb.from_user.id)
    L = LOCALES[lang]
    await cb.message.edit_text(L["entry_deleted"], reply_markup=book_kb(entry["book_id"], lang))

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

    words = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s AND is_active=TRUE", (book_id,), fetch=True, many=True)
    if not words:
        await cb.message.edit_text(L["empty_book"], reply_markup=book_kb(book_id, lang))
        return

    await state.set_state(VocabStates.practicing)
    await state.update_data(book_id=book_id, words=words, correct=0, wrong=0)

    await ask_question(cb.message, words, lang)

async def ask_question(msg: Message, words: List[Dict[str, Any]], lang: str):
    L = LOCALES[lang]
    entry = random.choice(words)
    ask_src = random.choice([True, False])

    presented = entry["word_src"] if ask_src else entry["word_trg"]
    correct = entry["word_trg"] if ask_src else entry["word_src"]

    pool = [w["word_trg"] if ask_src else w["word_src"] for w in words if w["id"] != entry["id"]]
    wrongs = random.sample(pool, min(3, len(pool)))
    options = wrongs + [correct]
    random.shuffle(options)

    buttons, row = [], []
    for i, opt in enumerate(options, start=1):
        row.append(InlineKeyboardButton(text=opt, callback_data=f"ans:{opt}:{correct}"))
        if i % 2 == 0:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text=L["finish"], callback_data="practice:finish")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await msg.edit_text(L["question"].format(word=presented), reply_markup=kb)
    except Exception:
        await msg.answer(L["question"].format(word=presented), reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_answer(cb: CallbackQuery, state: FSMContext):
    _, chosen, correct = cb.data.split(":", 2)
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()
    correct_count = data.get("correct", 0)
    wrong_count = data.get("wrong", 0)

    if chosen == correct:
        await cb.answer(L["correct"])
        correct_count += 1
    else:
        await cb.answer(L["wrong"].format(correct=correct))
        wrong_count += 1

    await state.update_data(correct=correct_count, wrong=wrong_count)
    await ask_question(cb.message, data["words"], lang)

@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_finish(cb: CallbackQuery, state: FSMContext):
    user_id = cb.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]

    data = await state.get_data()
    total = data.get("correct", 0) + data.get("wrong", 0)
    text = L["results"].format(total=total, correct=data.get("correct", 0), wrong=data.get("wrong", 0))

    try:
        await cb.message.edit_text(text, reply_markup=main_menu_kb(lang))
    except Exception:
        await cb.message.answer(text, reply_markup=main_menu_kb(lang))

    await state.clear()
    await cb.answer(L["session_end"])

# -------------------- Safety: fallback for unexpected messages --------------------
@router.message()
async def fallback_all_messages(msg: Message, state: FSMContext):
    # Keep this handler minimal and non-intrusive: only act if user in specific states
    data = await state.get_state()
    if not data:
        return  # ignore
    # if user stuck in some state, remind them that they can press back
    user_id = msg.from_user.id
    lang = await get_user_lang(user_id)
    L = LOCALES[lang]
    try:
        await msg.answer("🔔 Agar xatolik bo'lsa, Orqaga tugmasini bosing.", reply_markup=back_to_cabinet_kb(lang))
    except Exception:
        pass

# End of file