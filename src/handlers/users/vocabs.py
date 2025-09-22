import asyncio import random import io import csv import math from typing import List, Dict, Any, Optional, Tuple

from aiogram import Router from aiogram.types import ( Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputFile ) from aiogram.filters import Command from aiogram.fsm.context import FSMContext from aiogram.fsm.state import StatesGroup, State

from config import db

router = Router()

-------------------- Localization --------------------

LOCALES = { "uz": { "cabinet": "📚 Kabinet", "choose_lang": "Tilni tanlang:", "my_books": "📖 Mening lug'atlarim", "new_book": "➕ Yangi lug'at", "settings": "⚙️ Sozlamalar", "back": "🔙 Orqaga", "practice": "▶ Mashq", "add_words": "➕ So'z qo'shish", "delete": "❌ O‘chirish", "confirm_delete": "❓ Ushbu lug‘atni o‘chirishga ishonchingiz komilmi?", "yes": "✅ Ha", "no": "❌ Yo‘q", "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}", "no_books": "Sizda hali lug'at yo'q.", "enter_book_name": "Yangi lug'at nomini kiriting:", "book_created": "✅ Lug'at yaratildi: {name} (id={id})", "book_exists": "❌ Bu nom bilan lug'at mavjud.", "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).", "added_pairs": "✅ {n} ta juftlik qo'shildi. Yana yuborishingiz mumkin 👇", "empty_book": "❌ Bu lug'at bo'sh.", "question": "❓ {word}", "correct": "✅ To'g'ri", "wrong": "❌ Xato. To‘g‘ri javob: {correct}", "finish": "🏁 Tugatish", "session_end": "Mashq tugadi.", "back_to_book": "🔙 Orqaga", "main_menu": "🏠 Bosh menyu", "export_excel": "📤 Excelga eksport", "delete_pair": "🗑️ Juftni o'chirish", "add_now_question": "So'zlarni hozir qo'shasizmi?", "add_now_yes": "➕ Hozir qo'shish", "add_now_no": "🔙 Keyinroq", "pair_deleted": "✅ Juftlik o'chirildi.", "pair_not_found": "❌ Juftlik topilmadi.", "ask_pair_to_delete": "Juftlikni yuboring (format: word-translation) — o'chirish uchun.", "export_ready": "📤 Lug'at Excel (CSV) tayyor.", "page_indicator": "Sahifa {cur}/{tot}", "too_many_books": "📚 Sizda ko'p lug'atlar — sahifalash qo'llanildi.", "invalid_format": "❌ Xato format.", }, "en": { "cabinet": "📚 Cabinet", "choose_lang": "Choose your language:", "my_books": "📖 My books", "new_book": "➕ New book", "settings": "⚙️ Settings", "back": "🔙 Back", "practice": "▶ Practice", "add_words": "➕ Add words", "delete": "❌ Delete", "confirm_delete": "❓ Are you sure you want to delete this book?", "yes": "✅ Yes", "no": "❌ No", "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}", "no_books": "You have no books yet.", "enter_book_name": "Enter new book name:", "book_created": "✅ Book created: {name} (id={id})", "book_exists": "❌ Book with this name already exists.", "send_pairs": "Send word pairs (each line: word-translation).", "added_pairs": "✅ {n} pairs added. You can send more 👇", "empty_book": "❌ This book is empty.", "question": "❓ {word}", "correct": "✅ Correct", "wrong": "❌ Wrong. Correct: {correct}", "finish": "🏁 Finish", "session_end": "Practice finished.", "back_to_book": "🔙 Back", "main_menu": "🏠 Main menu", "export_excel": "📤 Export to Excel", "delete_pair": "🗑️ Delete pair", "add_now_question": "Add words now?", "add_now_yes": "➕ Add now", "add_now_no": "🔙 Later", "pair_deleted": "✅ Pair deleted.", "pair_not_found": "❌ Pair not found.", "ask_pair_to_delete": "Send pair (format: word-translation) to delete.", "export_ready": "📤 Book exported (CSV).", "page_indicator": "Page {cur}/{tot}", "too_many_books": "📚 You have many books — pagination used.", "invalid_format": "❌ Invalid format.", } }

-------------------- DB helpers --------------------

async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False): def run(): cur = db.cursor() cur.execute(query, params or ()) if fetch: if many: rows = cur.fetchall() cols = [d[0] for d in cur.description] return [dict(zip(cols, r)) for r in rows] else: row = cur.fetchone() if not row: return None cols = [d[0] for d in cur.description] return dict(zip(cols, row)) db.commit() return None return await asyncio.to_thread(run)

async def get_user_lang(user_id: int) -> str: row = await db_exec("SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True) return row["lang_code"] if row and row.get("lang_code") else "uz"

async def set_user_lang(user_id: int, lang: str): row = await db_exec("SELECT id FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True) if row: await db_exec("UPDATE accounts SET lang_code=%s WHERE id=%s", (lang, row["id"])) else: await db_exec("INSERT INTO accounts (user_id, lang_code) VALUES (%s,%s)", (user_id, lang))

-------------------- FSM --------------------

class VocabStates(StatesGroup): waiting_book_name = State() waiting_word_list = State() practicing = State() waiting_delete_pair = State()

-------------------- UI builders --------------------

PAGE_SIZE = 8

def cabinet_kb(lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")], [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books:page:1")], [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")] ])

def settings_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")], [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")] ])

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["practice"], callback_data=f"book:practice:{book_id}")], [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}"), InlineKeyboardButton(text=L["export_excel"], callback_data=f"book:export:{book_id}")], [InlineKeyboardButton(text=L["delete_pair"], callback_data=f"book:delpair:{book_id}"), InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete_confirm:{book_id}")], [InlineKeyboardButton(text=L["back"], callback_data="cab:books:page:1")] ])

def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["yes"], callback_data=f"book:delete_yes:{book_id}"), InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")] ])

def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data=f"book:open:{book_id}")] ])

def main_menu_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["main_menu"], callback_data="cab:back")] ])

def back_to_cabinet_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")] ])

def books_list_kb(rows: List[Dict[str, Any]], lang: str, page: int, total_pages: int) -> InlineKeyboardMarkup: L = LOCALES[lang] buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:open:{r['id']}")] for r in rows] nav_row = [] if page > 1: nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"cab:books:page:{page-1}")) nav_row.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back")) if page < total_pages: nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"cab:books:page:{page+1}")) buttons.append(nav_row) return InlineKeyboardMarkup(inline_keyboard=buttons)

-------------------- Cabinet --------------------

@router.message(Command("cabinet")) async def cmd_cabinet(msg: Message): lang = await get_user_lang(msg.from_user.id) L = LOCALES[lang] await msg.answer(L["cabinet"], reply_markup=cabinet_kb(lang))

@router.callback_query(lambda c: c.data and c.data.startswith("cab:")) async def cb_cabinet(cb: CallbackQuery, state: FSMContext): user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

if cb.data == "cab:settings":
    await cb.message.edit_text(L["choose_lang"], reply_markup=settings_kb(lang))
elif cb.data == "cab:back":
    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang))
elif cb.data == "cab:new":
    await cb.message.edit_text(L["enter_book_name"], reply_markup=back_to_cabinet_kb(lang))
    await state.set_state(VocabStates.waiting_book_name)
elif cb.data.startswith("cab:books:page:"):
    try:
        page = int(cb.data.split(":")[-1])
    except Exception:
        page = 1
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return
    total = len(rows)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    page_rows = rows[start:end]
    kb = books_list_kb(page_rows, lang, page, total_pages)
    indicator = L["page_indicator"].format(cur=page, tot=total_pages)
    try:
        await cb.message.edit_text(f"{L['my_books']}\n{indicator}", reply_markup=kb)
    except Exception:
        await cb.message.answer(f"{L['my_books']}\n{indicator}", reply_markup=kb)
elif cb.data == "cab:practice":
    # list books but only for practice selection
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return
    buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:practice_select:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
    try:
        await cb.message.edit_text(L["practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    except Exception:
        await cb.message.answer(L["practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(lambda c: c.data and c.data.startswith("lang:")) async def cb_change_lang(cb: CallbackQuery): lang = cb.data.split(":")[1] await set_user_lang(cb.from_user.id, lang) L = LOCALES[lang] await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang)) await cb.answer("Language changed ✅")

-------------------- Books --------------------

@router.message(VocabStates.waiting_book_name) async def add_book(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

name = msg.text.strip()
row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
if row:
    await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
    await state.clear()
    return

row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
await msg.answer(L["book_created"].format(name=name, id=row["id"]), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=L["add_now_yes"], callback_data=f"book:add_now:{row['id']}"),
     InlineKeyboardButton(text=L["add_now_no"], callback_data="cab:back")]
]))
await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:open:")) async def cb_book_open(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) try: await cb.message.edit_text(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang)) except Exception: await cb.message.answer(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:add_now:")) async def cb_book_add_now(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] try: await cb.message.edit_text(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang)) except Exception: await cb.message.answer(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang)) await state.update_data(book_id=book_id) await state.set_state(VocabStates.waiting_word_list)

-------- Delete book --------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_confirm:")) async def cb_book_delete_confirm(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] await cb.message.edit_text(L["confirm_delete"], reply_markup=confirm_delete_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_yes:")) async def cb_book_delete(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))

rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
                    (user_id,), fetch=True, many=True)
if not rows:
    await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
    return

buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:open:{r['id']}")] for r in rows]
buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
await cb.message.edit_text(L["my_books"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

-------- Add words --------

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:")) async def cb_book_add(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang]

try:
    await cb.message.edit_text(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))
except Exception:
    await cb.message.answer(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))

await state.update_data(book_id=book_id)
await state.set_state(VocabStates.waiting_word_list)

@router.message(VocabStates.waiting_word_list) async def add_words(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang] data = await state.get_data() book_id = data["book_id"]

lines = msg.text.strip().split("\n")
pairs = []
for line in lines:
    if "-" in line:
        w, t = line.split("-", 1)
        pairs.append((w.strip(), t.strip()))
if not pairs:
    await msg.answer(L["invalid_format"], reply_markup=add_words_back_kb(book_id, lang))
    return

for w, t in pairs:
    await db_exec("INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (book_id, w, t))

await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))
await state.clear()

-------------------- Export to CSV/Excel --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:export:")) async def cb_book_export(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang]

rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id", (book_id,), fetch=True, many=True)
if not rows:
    await cb.answer(L["empty_book"], show_alert=True)
    return

# create CSV in memory
s = io.StringIO()
writer = csv.writer(s)
writer.writerow(["word_src", "word_trg"])
for r in rows:
    writer.writerow([r["word_src"], r["word_trg"]])
content = s.getvalue().encode("utf-8-sig")
b = io.BytesIO(content)
b.seek(0)

try:
    await cb.message.answer_document(InputFile(b, filename=f"vocab_book_{book_id}.csv"), caption=L["export_ready"], reply_markup=book_kb(book_id, lang))
except Exception:
    await cb.answer(L["export_ready"])

-------------------- Delete pair --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delpair:")) async def cb_book_delpair(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] try: await cb.message.edit_text(L["ask_pair_to_delete"], reply_markup=add_words_back_kb(book_id, lang)) except Exception: await cb.message.answer(L["ask_pair_to_delete"], reply_markup=add_words_back_kb(book_id, lang)) await state.update_data(book_id=book_id) await state.set_state(VocabStates.waiting_delete_pair)

@router.message(VocabStates.waiting_delete_pair) async def handle_delete_pair(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang] data = await state.get_data() book_id = data.get("book_id")

if "-" not in msg.text:
    await msg.answer(L["invalid_format"], reply_markup=add_words_back_kb(book_id, lang))
    return

w, t = msg.text.split("-", 1)
w = w.strip()
t = t.strip()
res = await db_exec("DELETE FROM vocab_entries WHERE book_id=%s AND word_src=%s AND word_trg=%s RETURNING id", (book_id, w, t), fetch=True)
if res:
    await msg.answer(L["pair_deleted"], reply_markup=book_kb(book_id, lang))
else:
    await msg.answer(L["pair_not_found"], reply_markup=add_words_back_kb(book_id, lang))
await state.clear()

-------------------- Practice --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:practice_select:")) async def cb_book_practice_select(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) # reuse existing practice flow await cb.message.answer("Starting practice...") await cb_book_practice(cb, state)

@router.callback_query(lambda c: c.data and c.data.startswith("book:practice:")) async def cb_book_practice(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

words = await db_exec("SELECT id, word_src, word_trg FROM vocab_entries WHERE book_id=%s AND is_active=TRUE", (book_id,), fetch=True, many=True)
if not words:
    await cb.message.edit_text(L["empty_book"], reply_markup=book_kb(book_id, lang))
    return

await state.set_state(VocabStates.practicing)
await state.update_data(book_id=book_id, words=words, correct=0, wrong=0)

await ask_question(cb.message, words, lang)

async def ask_question(msg: Message, words: List[Dict[str, Any]], lang: str): L = LOCALES[lang] entry = random.choice(words) ask_src = random.choice([True, False])

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

@router.callback_query(lambda c: c.data and c.data.startswith("ans:")) async def cb_answer(cb: CallbackQuery, state: FSMContext): _, chosen, correct = cb.data.split(":", 2) user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

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

@router.callback_query(lambda c: c.data == "practice:finish") async def cb_finish(cb: CallbackQuery, state: FSMContext): user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

data = await state.get_data()
total = data.get("correct", 0) + data.get("wrong", 0)
text = L["results"].format(total=total, correct=data.get("correct", 0), wrong=data.get("wrong", 0))

try:
    await cb.message.edit_text(text, reply_markup=main_menu_kb(lang))
except Exception:
    await cb.message.answer(text, reply_markup=main_menu_kb(lang))

await state.clear()
await cb.answer(L["session_end"])

End of file

