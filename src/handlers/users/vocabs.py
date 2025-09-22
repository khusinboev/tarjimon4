import asyncio import random import io import csv from typing import List, Dict, Any, Optional, Tuple

from aiogram import Router from aiogram.types import ( Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputFile ) from aiogram.filters import Command from aiogram.fsm.context import FSMContext from aiogram.fsm.state import StatesGroup, State from config import db

router = Router()

-------------------- Localization --------------------

LOCALES = { "uz": { "cabinet": "📚 Kabinet", "choose_lang": "Tilni tanlang:", "my_books": "📖 Mening lug'atlarim", "new_book": "➕ Yangi lug'at", "settings": "⚙️ Sozlamalar", "back": "🔙 Orqaga", "practice": "▶ Mashq", "add_words": "➕ So'z qo'shish", "delete": "❌ O‘chirish", "confirm_delete": "❓ Ushbu lug‘atni o‘chirishga ishonchingiz komilmi?", "yes": "✅ Ha", "no": "❌ Yo‘q", "results": "📊 Natijalar:\nJami: {total}\nTo'g'ri: {correct}\nXato: {wrong}", "no_books": "Sizda hali lug'at yo'q.", "enter_book_name": "Yangi lug'at nomini kiriting:", "book_created": "✅ Lug'at yaratildi: {name} (id={id})", "book_exists": "❌ Bu nom bilan lug'at mavjud.", "send_pairs": "So'zlarni yuboring (har qatorda: word-translation).", "added_pairs": "✅ {n} ta juftlik qo'shildi. Yana yuborishingiz mumkin 👇", "empty_book": "❌ Bu lug'at bo'sh.", "question": "❓ {word}", "correct": "✅ To'g'ri", "wrong": "❌ Xato. To‘g‘ri javob: {correct}", "finish": "🏁 Tugatish", "session_end": "Mashq tugadi.", "back_to_book": "🔙 Orqaga", "main_menu": "🏠 Bosh menyu", "ask_add_after_create": "Lug'at yaratildi. So‘zlarni hozir qo‘shmoqchimisiz?", "yes_add": "➕ Ha, qo'shaman", "no_later": "🔙 Keyinroq", "export_excel": "📤 Excelga eksport", "manage_book": "⚙️ Lug'atni boshqarish", "delete_pair_prompt": "O'chirmoqchi bo'lgan juftlikni yuboring (word-translation):", "pair_deleted": "✅ Juftlik o'chirildi.", "pair_not_found": "❌ Bunday juftlik topilmadi.", "no_entries": "Bu lug'atda so'zlar yo'q.", "page": "Sahifa {cur}/{total}" }, "en": { "cabinet": "📚 Cabinet", "choose_lang": "Choose your language:", "my_books": "📖 My books", "new_book": "➕ New book", "settings": "⚙️ Settings", "back": "🔙 Back", "practice": "▶ Practice", "add_words": "➕ Add words", "delete": "❌ Delete", "confirm_delete": "❓ Are you sure you want to delete this book?", "yes": "✅ Yes", "no": "❌ No", "results": "📊 Results:\nTotal: {total}\nCorrect: {correct}\nWrong: {wrong}", "no_books": "You have no books yet.", "enter_book_name": "Enter new book name:", "book_created": "✅ Book created: {name} (id={id})", "book_exists": "❌ Book with this name already exists.", "send_pairs": "Send word pairs (each line: word-translation).", "added_pairs": "✅ {n} pairs added. You can send more 👇", "empty_book": "❌ This book is empty.", "question": "❓ {word}", "correct": "✅ Correct", "wrong": "❌ Wrong. Correct: {correct}", "finish": "🏁 Finish", "session_end": "Practice finished.", "back_to_book": "🔙 Back", "main_menu": "🏠 Main menu", "ask_add_after_create": "Book created. Add words now?", "yes_add": "➕ Yes, add", "no_later": "🔙 Later", "export_excel": "📤 Export to Excel", "manage_book": "⚙️ Manage book", "delete_pair_prompt": "Send the pair to delete (word-translation):", "pair_deleted": "✅ Pair deleted.", "pair_not_found": "❌ Pair not found.", "no_entries": "This book has no entries.", "page": "Page {cur}/{total}" } }

-------------------- DB helpers --------------------

async def db_exec(query: str, params: tuple = None, fetch: bool = False, many: bool = False): def run(): cur = db.cursor() cur.execute(query, params or ()) if fetch: if many: rows = cur.fetchall() cols = [d[0] for d in cur.description] return [dict(zip(cols, r)) for r in rows] else: row = cur.fetchone() if not row: return None cols = [d[0] for d in cur.description] return dict(zip(cols, row)) db.commit() return None

return await asyncio.to_thread(run)

async def get_user_lang(user_id: int) -> str: row = await db_exec("SELECT lang_code FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True) return row["lang_code"] if row and row.get("lang_code") else "uz"

async def set_user_lang(user_id: int, lang: str): row = await db_exec("SELECT id FROM accounts WHERE user_id=%s ORDER BY id DESC LIMIT 1", (user_id,), fetch=True) if row: await db_exec("UPDATE accounts SET lang_code=%s WHERE id=%s", (lang, row["id"])) else: await db_exec("INSERT INTO accounts (user_id, lang_code) VALUES (%s,%s)", (user_id, lang))

-------------------- FSM --------------------

class VocabStates(StatesGroup): waiting_book_name = State() waiting_word_list = State() practicing = State() waiting_delete_pair = State()

-------------------- UI builders --------------------

PAGE_SIZE = 6

def cabinet_kb(lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["practice"], callback_data="cab:practice")], [InlineKeyboardButton(text=L["my_books"], callback_data="cab:books")], [InlineKeyboardButton(text=L["settings"], callback_data="cab:settings")] ])

def settings_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang:uz"), InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")], [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")] ])

def book_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["practice"], callback_data=f"book:practice:{book_id}")], [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")], [InlineKeyboardButton(text=L["manage_book"], callback_data=f"book:manage:{book_id}")], [InlineKeyboardButton(text=L["back"], callback_data="cab:books")] ])

def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: L = LOCALES[lang] return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["yes"], callback_data=f"book:delete_yes:{book_id}"), InlineKeyboardButton(text=L["no"], callback_data=f"book:open:{book_id}")] ])

def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["back_to_book"], callback_data=f"book:open:{book_id}")] ])

def main_menu_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["main_menu"], callback_data="cab:back")] ])

def back_to_cabinet_kb(lang: str) -> InlineKeyboardMarkup: return InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=LOCALES[lang]["back"], callback_data="cab:back")] ])

def books_list_kb(books: List[Dict[str, Any]], lang: str, page: int = 1) -> InlineKeyboardMarkup: L = LOCALES[lang] start = (page - 1) * PAGE_SIZE end = start + PAGE_SIZE chunk = books[start:end] buttons = [[InlineKeyboardButton(text=b["name"], callback_data=f"book:open:{b['id']}")] for b in chunk]

nav = []
total_pages = (len(books) + PAGE_SIZE - 1) // PAGE_SIZE
if page > 1:
    nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"mybooks:page:{page-1}"))
nav.append(InlineKeyboardButton(text=L["page"].format(cur=page, total=total_pages), callback_data="mybooks:noop"))
if page < total_pages:
    nav.append(InlineKeyboardButton(text="➡️", callback_data=f"mybooks:page:{page+1}"))
if nav:
    buttons.append(nav)

buttons.append([InlineKeyboardButton(text=L["new_book"], callback_data="mybooks:new")])
buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
return InlineKeyboardMarkup(inline_keyboard=buttons)

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
elif cb.data == "cab:books":
    # Show my books (paginated)
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return
    await cb.message.edit_text(L["my_books"], reply_markup=books_list_kb(rows, lang, page=1))
elif cb.data == "cab:practice":
    # show list of books to practice
    rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
    if not rows:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
        return
    buttons = [[InlineKeyboardButton(text=r["name"], callback_data=f"book:practice:{r['id']}")] for r in rows]
    buttons.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])
    await cb.message.edit_text(L["practice"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@router.callback_query(lambda c: c.data and c.data.startswith("lang:")) async def cb_change_lang(cb: CallbackQuery): lang = cb.data.split(":")[1] await set_user_lang(cb.from_user.id, lang) L = LOCALES[lang] await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(lang)) await cb.answer("Language changed ✅")

-------------------- Books / Create --------------------

@router.message(VocabStates.waiting_book_name) async def add_book(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

name = msg.text.strip()
row = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
if row:
    await msg.answer(L["book_exists"], reply_markup=main_menu_kb(lang))
    await state.clear()
    return

row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name), fetch=True)
await msg.answer(L["book_created"].format(name=name, id=row["id"]), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=L["yes_add"], callback_data=f"book:add_after_create:{row['id']}")],
    [InlineKeyboardButton(text=L["no_later"], callback_data="cab:books")]
]))
await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:add_after_create:")) async def cb_add_after_create(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] try: await cb.message.edit_text(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang)) except Exception: await cb.message.answer(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang)) # set state and store book_id state = cb._bot['fsm_context'] if hasattr(cb, '_bot') else None # we cannot access FSMContext here easily, so ask user to send command instead # Simpler: set a hidden state by asking them to press Add words from book menu

-------------------- Book open / manage --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:open:") or c.data and c.data.startswith("book:manage:")) async def cb_book_open(cb: CallbackQuery, state: FSMContext): # unified handler for open & manage parts = cb.data.split(":") action = parts[1] book_id = int(parts[2]) lang = await get_user_lang(cb.from_user.id) try: await cb.message.edit_text(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang)) except Exception: await cb.message.answer(f"📖 Book {book_id}", reply_markup=book_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:manage:")) async def cb_book_manage(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] kb = InlineKeyboardMarkup(inline_keyboard=[ [InlineKeyboardButton(text=L["export_excel"], callback_data=f"book:export:{book_id}")], [InlineKeyboardButton(text=L["add_words"], callback_data=f"book:add:{book_id}")], [InlineKeyboardButton(text=L["delete"], callback_data=f"book:delete_confirm:{book_id}")], [InlineKeyboardButton(text=L["back"], callback_data=f"book:open:{book_id}")] ]) try: await cb.message.edit_text(L["manage_book"], reply_markup=kb) except Exception: await cb.message.answer(L["manage_book"], reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("book:export:")) async def cb_book_export(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang]

rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s ORDER BY id", (book_id,), fetch=True, many=True)
if not rows:
    await cb.answer(L["no_entries"])
    return

output = io.StringIO()
writer = csv.writer(output)
writer.writerow(["word_src", "word_trg"])  # header
for r in rows:
    writer.writerow([r["word_src"], r["word_trg"]])
output.seek(0)

bio = io.BytesIO(output.getvalue().encode('utf-8'))
bio.name = f"vocab_book_{book_id}.csv"
try:
    await cb.message.answer_document(InputFile(bio))
except Exception:
    await cb.answer("Failed to send file.")

-------------------- Delete book --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_confirm:")) async def cb_book_delete_confirm(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] await cb.message.edit_text(L["confirm_delete"], reply_markup=confirm_delete_kb(book_id, lang))

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_yes:")) async def cb_book_delete(cb: CallbackQuery): book_id = int(cb.data.split(":")[2]) user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))

rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
                     (user_id,), fetch=True, many=True)
if not rows:
    await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
    return

await cb.message.edit_text(L["my_books"], reply_markup=books_list_kb(rows, lang, page=1))

-------------------- Add words --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:add:")) async def cb_book_add(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang]

try:
    await cb.message.edit_text(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))
except Exception:
    await cb.message.answer(L["send_pairs"], reply_markup=add_words_back_kb(book_id, lang))

await state.update_data(book_id=book_id)
await state.set_state(VocabStates.waiting_word_list)

@router.message(VocabStates.waiting_word_list) async def add_words(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang] data = await state.get_data() book_id = data.get("book_id")

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
    await db_exec("INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (book_id, w, t))

await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))
await state.clear()

-------------------- Practice --------------------

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

-------------------- Pagination for my books --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("mybooks:page:")) async def cb_mybooks_page(cb: CallbackQuery): page = int(cb.data.split(":")[2]) user_id = cb.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang]

rows = await db_exec("SELECT id, name FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC", (user_id,), fetch=True, many=True)
if not rows:
    await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
    return
await cb.message.edit_text(L["my_books"], reply_markup=books_list_kb(rows, lang, page=page))

-------------------- Delete pair flow --------------------

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete_pair:")) async def cb_book_delete_pair(cb: CallbackQuery, state: FSMContext): book_id = int(cb.data.split(":")[2]) lang = await get_user_lang(cb.from_user.id) L = LOCALES[lang] await cb.message.edit_text(L["delete_pair_prompt"], reply_markup=add_words_back_kb(book_id, lang)) await state.update_data(book_id=book_id) await state.set_state(VocabStates.waiting_delete_pair)

@router.message(VocabStates.waiting_delete_pair) async def delete_pair(msg: Message, state: FSMContext): user_id = msg.from_user.id lang = await get_user_lang(user_id) L = LOCALES[lang] data = await state.get_data() book_id = data.get("book_id")

line = msg.text.strip()
if "-" not in line:
    await msg.answer("❌ Xato format.", reply_markup=add_words_back_kb(book_id, lang))
    return
w, t = [s.strip() for s in line.split("-", 1)]
row = await db_exec("SELECT id FROM vocab_entries WHERE book_id=%s AND word_src=%s AND word_trg=%s", (book_id, w, t), fetch=True)
if not row:
    await msg.answer(L["pair_not_found"], reply_markup=add_words_back_kb(book_id, lang))
    await state.clear()
    return
await db_exec("DELETE FROM vocab_entries WHERE id=%s", (row["id"],))
await msg.answer(L["pair_deleted"], reply_markup=add_words_back_kb(book_id, lang))
await state.clear()

Done - module

