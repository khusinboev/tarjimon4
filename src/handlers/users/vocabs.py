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

@router.callback_query(lambda c: c.data == "cab:back")
async def cb_back_to_cabinet(cb: CallbackQuery):
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    await cb.message.edit_text(L["cabinet"], reply_markup=cabinet_kb(data["lang"]))
    await cb.answer()

@router.callback_query(lambda c: c.data == "cab:settings")
async def cb_settings(cb: CallbackQuery):
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    await cb.message.edit_text(L["choose_lang"], reply_markup=settings_kb(data["lang"]))
    await cb.answer()

@router.callback_query(lambda c: c.data == "cab:books")
async def cb_my_books(cb: CallbackQuery):
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    if not data["books"]:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(data["lang"]))
    else:
        await cb.message.edit_text(L["my_books"], reply_markup=books_kb(data["books"], data["lang"]))
    await cb.answer()

@router.callback_query(lambda c: c.data == "cab:public_books")
async def cb_public_books(cb: CallbackQuery):
    lang = (await get_user_data(cb.from_user.id))["lang"]
    L = get_locale(lang)
    books = await db_exec(
        "SELECT id, name, user_id FROM vocab_books WHERE is_public=TRUE ORDER BY created_at DESC LIMIT 50",
        fetch=True, many=True
    )
    if not books:
        await cb.message.edit_text(L["no_public_books"], reply_markup=cabinet_kb(lang))
    else:
        buttons = [
            InlineKeyboardButton(
                text=f"{b['name']} 🌐 (id={b['id']})",
                callback_data=f"public_book:{b['id']}"
            ) for b in books
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=two_col_rows(buttons) + [
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        await cb.message.edit_text(L["public_books"], reply_markup=kb)
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:"))
async def cb_book_open(cb: CallbackQuery):
    if any(cb.data.startswith(f"book:{p}:") for p in ["practice", "add", "delete", "export", "toggle_public"]):
        return
    book_id = int(cb.data.split(":")[1])
    book = await get_book_details(book_id)
    if not book:
        await cb.answer("❌ Lug'at topilmadi.", show_alert=True)
        return
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    is_owner = book["user_id"] == cb.from_user.id
    await cb.message.edit_text(f"{L['my_books']}: {book['name']}",
                               reply_markup=book_kb(book_id, data["lang"], book["is_public"], is_owner))
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("public_book:"))
async def cb_public_book_open(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[1])
    book = await get_book_details(book_id)
    if not book or not book["is_public"]:
        await cb.answer("❌ Public lug'at topilmadi.", show_alert=True)
        return
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    is_owner = book["user_id"] == cb.from_user.id
    await cb.message.edit_text(f"{L['public_books']}: {book['name']}",
                               reply_markup=book_kb(book_id, data["lang"], True, is_owner))
    await cb.answer()

# =====================================================
# 📌 Practice
# =====================================================
@router.callback_query(lambda c: c.data == "cab:practice")
async def cb_practice_section(cb: CallbackQuery):
    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]
    L = get_locale(lang)
    books = user_data["books"] + await db_exec(
        "SELECT id, name, is_public FROM vocab_books WHERE is_public=TRUE ORDER BY created_at DESC LIMIT 50",
        fetch=True, many=True
    )
    if not books:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(lang))
    else:
        await cb.message.edit_text(L["practice_section"], reply_markup=books_kb(books, lang, practice_mode=True))
    await cb.answer()

@router.callback_query(lambda c: c.data and (c.data.startswith("practice_book:") or c.data.startswith("book:practice:")))
async def cb_practice_start(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[-1])
    rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s",
                         (book_id,), fetch=True, many=True)
    if len(rows) < 4:
        lang = (await get_user_data(cb.from_user.id))["lang"]
        await cb.answer("❌ " + get_locale(lang)["empty_book"], show_alert=True)
        return

    random.shuffle(rows)
    await state.set_state(VocabStates.practicing)
    await state.update_data(
        book_id=book_id, words=rows, index=0,
        correct=0, wrong=0, total=len(rows), answers=0
    )
    lang = (await get_user_data(cb.from_user.id))["lang"]
    await send_next_question(cb.message, state, lang)
    await cb.answer()

async def send_next_question(msg: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    words, index = data["words"], data["index"]
    L = get_locale(lang)

    if index >= len(words):
        index = 0
        random.shuffle(words)
        await state.update_data(words=words, index=0)
        data = await state.get_data()

    current = words[index]
    correct_answer = current["word_trg"]
    options = [correct_answer]
    while len(options) < 4 and len(options) < len(words):
        cand = random.choice(words)["word_trg"]
        if cand not in options:
            options.append(cand)
    random.shuffle(options)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=o, callback_data=f"ans:{index}:{o}")] for o in options
    ] + [
        [InlineKeyboardButton(text=L["finish"], callback_data="practice:finish")],
        [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
    ])

    await msg.edit_text(L["question"].format(word=current["word_src"]), reply_markup=kb)

@router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    _, idx_str, chosen = cb.data.split(":", 2)
    idx = int(idx_str)
    data = await state.get_data()
    if idx >= len(data["words"]):
        await cb.answer("❌", show_alert=True)
        return

    current = data["words"][idx]
    correct = current["word_trg"]
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])

    if chosen == correct:
        data["correct"] += 1
        await cb.answer(L["correct"])
    else:
        data["wrong"] += 1
        await cb.answer(L["wrong"].format(correct=correct), show_alert=True)

    data["answers"] += 1
    data["index"] = idx + 1
    await state.update_data(**data)
    await send_next_question(cb.message, state, (await get_user_data(cb.from_user.id))["lang"])

@router.callback_query(lambda c: c.data == "practice:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    total, answers = data.get("total", 0), data.get("answers", 0)
    correct, wrong = data.get("correct", 0), data.get("wrong", 0)
    percent = (correct / answers * 100) if answers else 0
    lang = (await get_user_data(cb.from_user.id))["lang"]
    L = get_locale(lang)

    full_text = f"{L['results_header']}\n\n" + \
                L["results_lines"].format(unique=total, answers=answers, correct=correct, wrong=wrong, percent=percent)
    await cb.message.edit_text(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(lang))
    await state.clear()
    await cb.answer()

# =====================================================
# 📌 Book management: add, delete, export, toggle_public
# =====================================================
@router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
async def cb_book_add(cb: CallbackQuery, state: FSMContext):
    book_id = int(cb.data.split(":")[2])
    book = await get_book_details(book_id)
    if not book or book["user_id"] != cb.from_user.id:
        await cb.answer("❌ Bu lug'at sizniki emas.", show_alert=True)
        return
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(L["send_pairs"], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L["cancel"], callback_data="cab:books")]]
    ))
    await state.set_state(VocabStates.waiting_word_list)
    await state.update_data(book_id=book_id)
    await cb.answer()

@router.message(VocabStates.waiting_word_list)
async def process_word_list(msg: Message, state: FSMContext):
    data = await state.get_data()
    book_id = data.get("book_id")
    if not book_id:
        await msg.answer("❌ Lug'at topilmadi.")
        await state.clear()
        return
    pairs = [line.split("-", 1) for line in msg.text.splitlines() if "-" in line]
    pairs = [(a.strip(), b.strip()) for a, b in pairs if a.strip() and b.strip()]
    L = get_locale((await get_user_data(msg.from_user.id))["lang"])
    if not pairs:
        await msg.answer("❌ Juftlik topilmadi.")
        return
    count = 0
    for src, trg in pairs:
        res = await db_exec(
            "INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) "
            "ON CONFLICT DO NOTHING RETURNING id", (book_id, src, trg), fetch=True
        )
        if res:
            count += 1
    await msg.answer(L["added_pairs"].format(n=count),
                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                         [InlineKeyboardButton(text=L["back"], callback_data="cab:books")]
                     ]))
    await state.clear()

@router.callback_query(lambda c: c.data and c.data.startswith("book:delete:"))
async def cb_book_delete(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    book = await get_book_details(book_id)
    if not book or book["user_id"] != cb.from_user.id:
        await cb.answer("❌ Bu lug'at sizniki emas.", show_alert=True)
        return
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(L["confirm_delete"], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L["yes"], callback_data=f"book:confirm_delete:{book_id}"),
                          InlineKeyboardButton(text=L["no"], callback_data="cab:books")]]
    ))
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:confirm_delete:"))
async def cb_book_confirm_delete(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    book = await get_book_details(book_id)
    if not book or book["user_id"] != cb.from_user.id:
        await cb.answer("❌ Sizga tegishli emas.", show_alert=True)
        return
    await db_exec("DELETE FROM vocab_books WHERE id=%s", (book_id,))
    books = await db_exec("SELECT id,name,is_public FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
                          (cb.from_user.id,), fetch=True, many=True)
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(L["my_books"], reply_markup=books_kb(books, (await get_user_data(cb.from_user.id))["lang"]))
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:export:"))
async def cb_book_export(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    book = await get_book_details(book_id)
    if not book:
        await cb.answer("❌ Lug'at topilmadi.", show_alert=True)
        return
    path = await export_book_to_excel(book_id, cb.from_user.id)
    await cb.message.reply_document(FSInputFile(path))
    os.remove(path)
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(f"{L['my_books']}: {book['name']}",
                               reply_markup=book_kb(book_id, L, book["is_public"], book["user_id"] == cb.from_user.id))
    await cb.answer()

@router.callback_query(lambda c: c.data and c.data.startswith("book:toggle_public:"))
async def cb_book_toggle_public(cb: CallbackQuery):
    book_id = int(cb.data.split(":")[2])
    book = await get_book_details(book_id)
    if not book or book["user_id"] != cb.from_user.id:
        await cb.answer("❌ Sizga tegishli emas.", show_alert=True)
        return
    new_status = not book["is_public"]
    await db_exec("UPDATE vocab_books SET is_public=%s WHERE id=%s", (new_status, book_id))
    books = await db_exec("SELECT id,name,is_public FROM vocab_books WHERE user_id=%s ORDER BY created_at DESC",
                          (cb.from_user.id,), fetch=True, many=True)
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    msg = L["toggled_public"] if new_status else L["toggled_private"]
    await cb.message.edit_text(L["my_books"], reply_markup=books_kb(books, (await get_user_data(cb.from_user.id))["lang"]))
    await cb.answer(msg)

@router.callback_query(lambda c: c.data == "cab:new")
async def cb_new_book(cb: CallbackQuery, state: FSMContext):
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(L["enter_book_name"], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L["cancel"], callback_data="cab:books")]]
    ))
    await state.set_state(VocabStates.waiting_book_name)
    await cb.answer()

@router.message(VocabStates.waiting_book_name)
async def process_book_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    user_id = msg.from_user.id
    L = get_locale((await get_user_data(user_id))["lang"])
    exists = await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True)
    if exists:
        await msg.answer(L["book_exists"])
        return
    res = await db_exec(
        "INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id",
        (user_id, name), fetch=True
    )
    book_id = res["id"]
    await msg.answer(L["book_created"].format(name=name, id=book_id))
    await msg.answer(L["send_pairs"], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L["back"], callback_data="cab:books")]]
    ))
    await state.set_state(VocabStates.waiting_word_list)
    await state.update_data(book_id=book_id)
