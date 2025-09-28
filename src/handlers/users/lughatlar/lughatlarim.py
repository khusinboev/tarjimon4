from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from openpyxl import Workbook

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, export_book_to_excel, cabinet_kb
)

lughatlarim_router = Router()


# =====================================================
# 🔌 FSM States
# =====================================================
class LughatStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()


# =====================================================
# 🔌 UI Builders
# =====================================================
def books_kb(books, lang: str) -> InlineKeyboardMarkup:
    """Shaxsiy lug'atlar ro'yxati klaviaturasi."""
    L = get_locale(lang)
    btns = []
    for b in books:
        btns.append(InlineKeyboardButton(text=b["name"], callback_data=f"lughat:open:{b['id']}"))

    btns.append(InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="lughat:new"))
    btns.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back"))
    return InlineKeyboardMarkup(inline_keyboard=two_col_rows(btns))


def book_detail_kb(book_id: int, is_public: bool, lang: str) -> InlineKeyboardMarkup:
    """Lug'at batafsil sahifasi klaviaturasi."""
    L = get_locale(lang)
    buttons = [
        [InlineKeyboardButton(text="➕ So'z qo'shish", callback_data=f"lughat:add:{book_id}")],
        [InlineKeyboardButton(text="📤 Export", callback_data=f"lughat:export:{book_id}")],
    ]

    # Ommaviylik tugmasi
    if is_public:
        buttons.append([InlineKeyboardButton(text="🔒 Shaxsiy qilish", callback_data=f"lughat:private:{book_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🌐 Ommaviy qilish", callback_data=f"lughat:public:{book_id}")])

    buttons.extend([
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"lughat:delete_confirm:{book_id}")],
        [InlineKeyboardButton(text=L["back"], callback_data="lughat:list")]
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_delete_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["yes"], callback_data=f"lughat:delete_yes:{book_id}")],
        [InlineKeyboardButton(text=L["no"], callback_data=f"lughat:open:{book_id}")]
    ])


def new_book_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L["cancel"], callback_data="lughat:list")]
    ])


def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Lug'atga qaytish", callback_data=f"lughat:open:{book_id}")]
    ])


# =====================================================
# 🔌 Handlers
# =====================================================

@lughatlarim_router.callback_query(lambda c: c.data == "lughat:list")
async def cb_lughatlarim(cb: CallbackQuery):
    """Lug'atlarim bo'limini ko'rsatish."""
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang, books = data["lang"], data["books"]
    L = get_locale(lang)

    if not books:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="lughat:new")],
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        await safe_edit_or_send(cb, "📚 Sizda hali lug'at yo'q.", kb, lang)
        return

    await safe_edit_or_send(cb, "📚 Lug'atlarim", books_kb(books, lang), lang)
    await cb.answer()


@lughatlarim_router.callback_query(lambda c: c.data == "lughat:new")
async def cb_new_book(cb: CallbackQuery, state: FSMContext):
    """Yangi lug'at yaratish."""
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)

    await safe_edit_or_send(cb, L["enter_book_name"], new_book_cancel_kb(lang), lang)
    await state.set_state(LughatStates.waiting_book_name)
    await cb.answer()


@lughatlarim_router.message(LughatStates.waiting_book_name)
async def add_book(msg: Message, state: FSMContext):
    """Lug'at nomini qabul qilish va yaratish."""
    user_id = msg.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    name = msg.text.strip()
    if await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L["back"], callback_data="lughat:list")]
        ])
        await msg.answer(L["book_exists"], reply_markup=kb)
        await state.clear()
        return

    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name),
                        fetch=True)
    book_id = row["id"] if row else None

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Lug'atlarim", callback_data="lughat:list")]
    ])
    await msg.answer(L["book_created"].format(name=name, id=book_id), reply_markup=kb)
    await state.clear()


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:open:"))
async def cb_book_open(cb: CallbackQuery):
    """Lug'at batafsil sahifasini ko'rsatish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Lug'at ma'lumotlarini olish
    book_data = await db_exec(
        "SELECT name, is_public FROM vocab_books WHERE id=%s AND user_id=%s",
        (book_id, user_id), fetch=True
    )

    if not book_data:
        await cb.answer("❌ Lug'at topilmadi!", show_alert=True)
        return

    data = await get_user_data(user_id)
    lang = data["lang"]

    text = f"📖 {book_data['name']}\n"
    text += f"🌐 Holat: {'Ommaviy' if book_data['is_public'] else 'Shaxsiy'}"

    await safe_edit_or_send(cb, text, book_detail_kb(book_id, book_data['is_public'], lang), lang)
    await cb.answer()


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:public:"))
async def cb_make_public(cb: CallbackQuery):
    """Lug'atni ommaviy qilish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    await db_exec("UPDATE vocab_books SET is_public=TRUE WHERE id=%s AND user_id=%s", (book_id, user_id))

    # Yangi holat bilan sahifani yangilash
    book_data = await db_exec(
        "SELECT name, is_public FROM vocab_books WHERE id=%s AND user_id=%s",
        (book_id, user_id), fetch=True
    )

    data = await get_user_data(user_id)
    lang = data["lang"]

    text = f"📖 {book_data['name']}\n"
    text += f"🌐 Holat: {'Ommaviy' if book_data['is_public'] else 'Shaxsiy'}"

    await safe_edit_or_send(cb, text, book_detail_kb(book_id, book_data['is_public'], lang), lang)
    await cb.answer("✅ Lug'at ommaviy qilindi!")


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:private:"))
async def cb_make_private(cb: CallbackQuery):
    """Lug'atni shaxsiy qilish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    await db_exec("UPDATE vocab_books SET is_public=FALSE WHERE id=%s AND user_id=%s", (book_id, user_id))

    # Yangi holat bilan sahifani yangilash
    book_data = await db_exec(
        "SELECT name, is_public FROM vocab_books WHERE id=%s AND user_id=%s",
        (book_id, user_id), fetch=True
    )

    data = await get_user_data(user_id)
    lang = data["lang"]

    text = f"📖 {book_data['name']}\n"
    text += f"🌐 Holat: {'Ommaviy' if book_data['is_public'] else 'Shaxsiy'}"

    await safe_edit_or_send(cb, text, book_detail_kb(book_id, book_data['is_public'], lang), lang)
    await cb.answer("✅ Lug'at shaxsiy qilindi!")


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:add:"))
async def cb_book_add_words(cb: CallbackQuery, state: FSMContext):
    """So'z qo'shish rejimini boshlash."""
    book_id = int(cb.data.split(":")[2])
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)

    await safe_edit_or_send(cb, L["send_pairs"], add_words_back_kb(book_id, lang), lang)
    await state.update_data(book_id=book_id)
    await state.set_state(LughatStates.waiting_word_list)
    await cb.answer()


@lughatlarim_router.message(LughatStates.waiting_word_list)
async def add_words(msg: Message, state: FSMContext):
    """So'zlarni qabul qilish va saqlash."""
    data = await state.get_data()
    book_id = data["book_id"]
    user_data = await get_user_data(msg.from_user.id)
    lang = user_data["lang"]
    L = get_locale(lang)

    lines = msg.text.strip().split("\n")
    pairs = [(w.strip(), t.strip()) for line in lines if "-" in line for w, t in [line.split("-", 1)]]

    if not pairs:
        await msg.answer("❌ Xato format. Misol: word-tarjima", reply_markup=add_words_back_kb(book_id, lang))
        return

    for w, t in pairs:
        await db_exec(
            "INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
            (book_id, w, t))

    await msg.answer(L["added_pairs"].format(n=len(pairs)), reply_markup=add_words_back_kb(book_id, lang))


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:export:"))
async def cb_book_export(cb: CallbackQuery):
    """Lug'atni export qilish."""
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

    # Lug'atlar ro'yxatiga qaytish
    refreshed_data = await get_user_data(user_id)
    if not refreshed_data["books"]:
        await cb.message.answer("📚 Sizda hali lug'at yo'q.", reply_markup=cabinet_kb(lang))
    else:
        await cb.message.answer("📚 Lug'atlarim", reply_markup=books_kb(refreshed_data["books"], lang))


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:delete_confirm:"))
async def cb_book_delete_confirm(cb: CallbackQuery):
    """O'chirish tasdig'ini so'rash."""
    book_id = int(cb.data.split(":")[2])
    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)

    await safe_edit_or_send(cb, L["confirm_delete"], confirm_delete_kb(book_id, lang), lang)
    await cb.answer()


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:delete_yes:"))
async def cb_book_delete(cb: CallbackQuery):
    """Lug'atni o'chirish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    await db_exec("DELETE FROM vocab_entries WHERE book_id=%s", (book_id,))
    await db_exec("DELETE FROM vocab_books WHERE id=%s AND user_id=%s", (book_id, user_id))

    data = await get_user_data(user_id)
    lang, books = data["lang"], data["books"]

    if not books:
        await safe_edit_or_send(cb, "📚 Sizda hali lug'at yo'q.", cabinet_kb(lang), lang)
    else:
        await safe_edit_or_send(cb, "📚 Lug'atlarim", books_kb(books, lang), lang)
    await cb.answer("✅ Lug'at o'chirildi!")