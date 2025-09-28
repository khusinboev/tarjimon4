from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from math import ceil

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, export_book_to_excel, cabinet_kb,
    get_paginated_books, create_paginated_kb, BOOKS_PER_PAGE
)

lughatlarim_router = Router()


# =====================================================
# 📌 FSM States
# =====================================================
class LughatStates(StatesGroup):
    waiting_book_name = State()
    waiting_word_list = State()


# =====================================================
# 📌 UI Builders
# =====================================================
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
        [InlineKeyboardButton(text=L["back"], callback_data="lughat:list:0")]
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
        [InlineKeyboardButton(text=L["cancel"], callback_data="lughat:list:0")]
    ])


def add_words_back_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Lug'atga qaytish", callback_data=f"lughat:open:{book_id}")]
    ])


# =====================================================
# 📌 Handlers
# =====================================================

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:list:"))
async def cb_lughatlarim(cb: CallbackQuery):
    """Lug'atlarim bo'limini ko'rsatish (sahifalangan)."""
    user_id = cb.from_user.id
    page = int(cb.data.split(":")[2]) if len(cb.data.split(":")) > 2 else 0

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    # Sahifalangan lug'atlarni olish (min_words=0 - barcha lug'atlar)
    books, total_count = await get_paginated_books(user_id, page, BOOKS_PER_PAGE, min_words=0)

    if not books and page == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi lug'at", callback_data="lughat:new")],
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        await safe_edit_or_send(cb, "📚 Sizda hali lug'at yo'q.", kb, lang)
        return

    if not books and page > 0:
        # Agar sahifada hech narsa bo'lmasa, birinchi sahifaga qaytarish
        await cb.answer("❌ Bu sahifada lug'at yo'q", show_alert=True)
        return

    total_pages = ceil(total_count / BOOKS_PER_PAGE)
    kb = create_paginated_kb(books, page, total_pages, "lughat", lang)

    header_text = f"📚 Lug'atlarim ({total_count} ta)"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    await safe_edit_or_send(cb, header_text, kb, lang)
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
    if len(name) > 100:
        await msg.answer("❌ Nom juda uzun (maksimal 100 belgi)", reply_markup=new_book_cancel_kb(lang))
        return

    if await db_exec("SELECT id FROM vocab_books WHERE user_id=%s AND name=%s", (user_id, name), fetch=True):
        await msg.answer(L["book_exists"], reply_markup=new_book_cancel_kb(lang))
        return

    row = await db_exec("INSERT INTO vocab_books (user_id, name) VALUES (%s,%s) RETURNING id", (user_id, name),
                        fetch=True)
    book_id = row["id"] if row else None

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Lug'atlarim", callback_data="lughat:list:0")]
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
        """SELECT name,
                  is_public,
                  created_at::date as created_date, (SELECT COUNT(*) FROM vocab_entries WHERE book_id = %s) as word_count
           FROM vocab_books
           WHERE id = %s
             AND user_id = %s""",
        (book_id, book_id, user_id), fetch=True
    )

    if not book_data:
        await cb.answer("❌ Lug'at topilmadi!", show_alert=True)
        return

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    status_text = L["status_public"] if book_data['is_public'] else L["status_private"]

    text = f"📖 {book_data['name']}\n"
    text += f"📊 {L['word_count']} {book_data['word_count']} ta\n"
    text += f"📅 {L['created']} {book_data['created_date']}\n"
    text += f"📹 Holat: {status_text}"

    await safe_edit_or_send(cb, text, book_detail_kb(book_id, book_data['is_public'], lang), lang)
    await cb.answer()


@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("lughat:public:"))
async def cb_make_public(cb: CallbackQuery):
    """Lug'atni ommaviy qilish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Avval lug'atda yetarli so'z borligini tekshirish
    word_count = await db_exec(
        "SELECT COUNT(*) as count FROM vocab_entries WHERE book_id=%s",
        (book_id,), fetch=True
    )

    if word_count["count"] < 4:
        await cb.answer("❌ Ommaviy qilish uchun kamida 4 ta so'z kerak!", show_alert=True)
        return

    await db_exec("UPDATE vocab_books SET is_public=TRUE WHERE id=%s AND user_id=%s", (book_id, user_id))

    # Yangi holat bilan sahifani yangilash
    book_data = await db_exec(
        """SELECT name,
                  is_public,
                  created_at::date as created_date,
                  (SELECT COUNT(*) FROM vocab_entries WHERE book_id = %s) as word_count
           FROM vocab_books
           WHERE id = %s
             AND user_id = %s""",
        (book_id, book_id, user_id), fetch=True
    )

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    status_text = L["status_public"] if book_data['is_public'] else L["status_private"]

    text = f"📖 {book_data['name']}\n"
    text += f"📊 {L['word_count']} {book_data['word_count']} ta\n"
    text += f"📅 {L['created']} {book_data['created_date']}\n"
    text += f"📹 Holat: {status_text}"

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
        """SELECT name,
                  is_public,
                  created_at::date as created_date,
                  (SELECT COUNT(*) FROM vocab_entries WHERE book_id = %s) as word_count
           FROM vocab_books
           WHERE id = %s
             AND user_id = %s""",
        (book_id, book_id, user_id), fetch=True
    )

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    status_text = L["status_public"] if book_data['is_public'] else L["status_private"]

    text = f"📖 {book_data['name']}\n"
    text += f"📊 {L['word_count']} {book_data['word_count']} ta\n"
    text += f"📅 {L['created']} {book_data['created_date']}\n"
    text += f"📹 Holat: {status_text}"

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
    pairs = []

    for line in lines:
        if "-" in line:
            parts = line.split("-", 1)
            if len(parts) == 2:
                word = parts[0].strip()
                translation = parts[1].strip()
                if word and translation:
                    pairs.append((word, translation))

    if not pairs:
        await msg.answer("❌ Xato format. Misol: word-tarjima", reply_markup=add_words_back_kb(book_id, lang))
        return

    added_count = 0
    for w, t in pairs:
        try:
            await db_exec(
                "INSERT INTO vocab_entries (book_id, word_src, word_trg) VALUES (%s,%s,%s)",
                (book_id, w, t))
            added_count += 1
        except:
            # Duplicate yoki boshqa xato bo'lsa, o'tkazib yuborish
            continue

    if added_count > 0:
        await msg.answer(L["added_pairs"].format(n=added_count), reply_markup=add_words_back_kb(book_id, lang))
    else:
        await msg.answer("❌ Hech qanday yangi so'z qo'shilmadi", reply_markup=add_words_back_kb(book_id, lang))


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
    books, total_count = await get_paginated_books(user_id, 0, BOOKS_PER_PAGE, min_words=0)
    if not books:
        await cb.message.answer("📚 Sizda hali lug'at yo'q.", reply_markup=cabinet_kb(lang))
    else:
        total_pages = ceil(total_count / BOOKS_PER_PAGE)
        kb = create_paginated_kb(books, 0, total_pages, "lughat", lang)
        header_text = f"📚 Lug'atlarim ({total_count} ta)"
        await cb.message.answer(header_text, reply_markup=kb)


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

    # Lug'atlar ro'yxatiga qaytish
    books, total_count = await get_paginated_books(user_id, 0, BOOKS_PER_PAGE, min_words=0)
    data = await get_user_data(user_id)
    lang = data["lang"]

    if not books:
        await safe_edit_or_send(cb, "📚 Sizda hali lug'at yo'q.", cabinet_kb(lang), lang)
    else:
        total_pages = ceil(total_count / BOOKS_PER_PAGE)
        kb = create_paginated_kb(books, 0, total_pages, "lughat", lang)
        header_text = f"📚 Lug'atlarim ({total_count} ta)"
        await safe_edit_or_send(cb, header_text, kb, lang)

    await cb.answer("✅ Lug'at o'chirildi!")