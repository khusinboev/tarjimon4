from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random
from math import ceil

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, cabinet_kb, get_paginated_books,
    create_paginated_kb, BOOKS_PER_PAGE
)

ommaviylar_router = Router()


# =====================================================
# 📌 FSM States
# =====================================================
class OmmaviyMashqStates(StatesGroup):
    practicing = State()


# =====================================================
# 📌 UI Builders
# =====================================================
def public_book_detail_kb(book_id: int, is_own: bool, lang: str) -> InlineKeyboardMarkup:
    """Ommaviy lug'at batafsil sahifasi klaviaturasi."""
    L = get_locale(lang)

    buttons = []
    buttons.append([InlineKeyboardButton(text="▶ Mashq boshlash", callback_data=f"ommaviy:start:{book_id}")])

    # Agar o'z lug'ati bo'lsa, boshqarish tugmalari
    if is_own:
        buttons.append([InlineKeyboardButton(text="⚙️ Boshqarish", callback_data=f"lughat:open:{book_id}")])

    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="ommaviy:list:0")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_mixed_books_kb(books: list, current_page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    """Aralash lug'atlar (o'ziki va begonalar) uchun klaviatura."""
    L = get_locale(lang)
    rows = []

    for book in books:
        is_own = book.get("is_own", False)
        emoji = "🌟" if is_own else "👥"  # O'zikilar uchun yulduz, begonalar uchun odamlar

        # Muallif ma'lumoti
        author_info = "Siz" if is_own else f"ID {book['author_id']}"
        text = f"{emoji} {book['name']} ({book['word_count']})\n   👤 {author_info}"

        callback = f"ommaviy:info:{book['id']}"
        rows.append([InlineKeyboardButton(text=book['name'], callback_data=callback)])

    # Sahifalash tugmalari
    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(text=L["prev_page"], callback_data=f"ommaviy:list:{current_page - 1}"))

        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text=L["next_page"], callback_data=f"ommaviy:list:{current_page + 1}"))

        if nav_row:
            rows.append(nav_row)

        # Sahifa ma'lumoti
        page_info = L["page_info"].format(current=current_page + 1, total=total_pages)
        rows.append([InlineKeyboardButton(text=page_info, callback_data="noop")])

    rows.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


async def get_mixed_public_books(user_id: int, page: int = 0, per_page: int = BOOKS_PER_PAGE):
    """O'z va boshqalarning ommaviy lug'atlarini olish."""
    offset = page * per_page

    query = """
            SELECT vb.id, \
                   vb.name, \
                   vb.is_public, \
                   vb.user_id, \
                   vb.created_at::date as created_date, COALESCE(a.user_id::text, 'Unknown') as author_name,
                   COUNT(ve.id)                                       as word_count,
                   CASE WHEN vb.user_id = %s THEN true ELSE false END as is_own,
                   vb.user_id                                         as author_id
            FROM vocab_books vb
                     LEFT JOIN accounts a ON vb.user_id = a.user_id
                     LEFT JOIN vocab_entries ve ON vb.id = ve.book_id
            WHERE vb.is_public = TRUE
            GROUP BY vb.id, vb.name, vb.is_public, vb.user_id, vb.created_at, a.user_id
            HAVING COUNT(ve.id) >= 4
            ORDER BY CASE WHEN vb.user_id = %s THEN 0 ELSE 1 END, -- O'z lug'atlari birinchi \
                     vb.created_at DESC
                LIMIT %s \
            OFFSET %s \
            """

    books = await db_exec(query, (user_id, user_id, per_page, offset), fetch=True, many=True)

    # Umumiy soni
    count_query = """
                  SELECT COUNT(DISTINCT vb.id) as count
                  FROM vocab_books vb
                      LEFT JOIN vocab_entries ve \
                  ON vb.id = ve.book_id
                  WHERE vb.is_public = TRUE
                  GROUP BY vb.id
                  HAVING COUNT (ve.id) >= 4 \
                  """

    count_result = await db_exec(count_query, (), fetch=True, many=True)
    total_count = len(count_result) if count_result else 0

    return books or [], total_count


# =====================================================
# 📌 Handlers
# =====================================================

@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("ommaviy:list:"))
async def cb_ommaviylar(cb: CallbackQuery):
    """Ommaviy lug'atlar bo'limini ko'rsatish."""
    user_id = cb.from_user.id
    page = int(cb.data.split(":")[2]) if len(cb.data.split(":")) > 2 else 0

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    # Aralash ommaviy lug'atlarni olish
    books, total_count = await get_mixed_public_books(user_id, page, BOOKS_PER_PAGE)

    if not books and page == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        await safe_edit_or_send(cb, L["no_public_books"], kb, lang)
        return

    if not books and page > 0:
        await cb.answer("❌ Bu sahifada lug'at yo'q", show_alert=True)
        return

    total_pages = ceil(total_count / BOOKS_PER_PAGE)
    kb = create_mixed_books_kb(books, page, total_pages, lang)

    # O'z va begona lug'atlar sonini hisoblash
    own_count = sum(1 for book in books if book.get('is_own', False))
    others_count = len(books) - own_count

    header_text = f"🌐 Ommaviy lug'atlar ({total_count} ta)"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    if own_count > 0:
        header_text += f"\n🌟 Sizning: {own_count} ta"
    if others_count > 0:
        header_text += f"\n👥 Boshqalar: {others_count} ta"

    await safe_edit_or_send(cb, header_text, kb, lang)
    await cb.answer()


@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("ommaviy:info:"))
async def cb_public_book_info(cb: CallbackQuery):
    """Ommaviy lug'at haqida ma'lumot."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Lug'at ma'lumotlarini olish
    book_info = await db_exec("""
                              SELECT vb.name,
                                     vb.description,
                                     vb.user_id   as author_id,
                                     COUNT(ve.id) as word_count,
                                     vb.created_at::date as created_date, CASE WHEN vb.user_id = %s THEN true ELSE false END as is_own
                              FROM vocab_books vb
                                       LEFT JOIN vocab_entries ve ON vb.id = ve.book_id
                              WHERE vb.id = %s
                                AND vb.is_public = TRUE
                              GROUP BY vb.id, vb.name, vb.description, vb.user_id, vb.created_at
                              """, (user_id, book_id), fetch=True)

    if not book_info:
        await cb.answer("❌ Lug'at topilmadi!", show_alert=True)
        return

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    is_own = book_info["is_own"]
    author_text = "Siz" if is_own else f"ID {book_info['author_id']}"
    ownership_emoji = "🌟" if is_own else "👥"

    text = f"{ownership_emoji} {book_info['name']}\n"
    text += f"👤 {L['author']} {author_text}\n"
    text += f"📊 {L['word_count']} {book_info['word_count']} ta\n"
    text += f"📅 {L['created']} {book_info['created_date']}\n"

    if book_info['description']:
        text += f"📝 Tavsif: {book_info['description']}"

    await safe_edit_or_send(cb, text, public_book_detail_kb(book_id, is_own, lang), lang)
    await cb.answer()


@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("ommaviy:start:"))
async def cb_start_public_practice(cb: CallbackQuery, state: FSMContext):
    """Ommaviy lug'at bilan mashqni boshlash."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Lug'atdagi so'zlarni olish
    rows = await db_exec("""
                         SELECT ve.word_src, ve.word_trg
                         FROM vocab_entries ve
                                  JOIN vocab_books vb ON ve.book_id = vb.id
                         WHERE vb.id = %s
                           AND vb.is_public = TRUE
                         """, (book_id,), fetch=True, many=True)

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    if len(rows) < 4:
        await cb.answer("❌ " + L["empty_book"], show_alert=True)
        return

    random.shuffle(rows)
    await state.update_data(
        book_id=book_id, words=rows, index=0, correct=0, wrong=0, total=len(rows),
        answers=0, cycles=0, current_cycle_correct=0, current_cycle_wrong=0, cycles_stats=[],
        is_public=True  # Ommaviy lug'at ekanligini belgilash
    )
    await state.set_state(OmmaviyMashqStates.practicing)
    await send_next_public_question(cb.message, state, lang)
    await cb.answer()


async def send_next_public_question(msg: Message, state: FSMContext, lang: str):
    """Ommaviy mashq uchun keyingi savolni yuborish."""
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

    # To'g'ri javobdan boshqa variantlar tanlash
    while len(options) < 4 and len(options) < len(data["words"]):
        candidate = random.choice(data["words"])["word_trg"]
        if candidate not in seen:
            options.append(candidate)
            seen.add(candidate)

    random.shuffle(options)

    kb = InlineKeyboardMarkup(inline_keyboard=[
                                                  [InlineKeyboardButton(text=o,
                                                                        callback_data=f"ommaviy_ans:{index}:{o}")] for o
                                                  in options
                                              ] + [
                                                  [InlineKeyboardButton(text=L["finish"],
                                                                        callback_data="ommaviy:finish")],
                                                  [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
                                              ])

    progress_text = f"📊 {data.get('correct', 0)}/{data.get('answers', 0)} to'g'ri"
    question_text = f"{L['question'].format(word=current['word_src'])}\n\n{progress_text}"

    await msg.edit_text(question_text, reply_markup=kb)


@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("ommaviy_ans:"))
async def cb_public_practice_answer(cb: CallbackQuery, state: FSMContext):
    """Ommaviy mashq javobini tekshirish."""
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
    await send_next_public_question(cb.message, state, user_data["lang"])


@ommaviylar_router.callback_query(lambda c: c.data == "ommaviy:finish")
async def cb_public_practice_finish(cb: CallbackQuery, state: FSMContext):
    """Ommaviy mashqni tugatish."""
    data = await state.get_data()
    total_unique, total_answers = data.get("total", 0), data.get("answers", 0)
    total_correct, total_wrong = data.get("correct", 0), data.get("wrong", 0)
    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    full_text = f"{L['results_header']}\n\n{L['results_lines'].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)}"

    # Agar natija yaxshi bo'lsa, qo'shimcha motivatsiya
    if percent >= 80:
        full_text += "\n\n🎉 Ajoyib natija! Davom eting!"
    elif percent >= 60:
        full_text += "\n\n👍 Yaxshi natija! Yanada yaxshilashishga harakat qiling!"
    else:
        full_text += "\n\n💪 Mashq davom eting, natija yaxshilanadi!"

    await state.clear()
    await cb.message.edit_text(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()