from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random
from math import ceil

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, cabinet_kb, BOOKS_PER_PAGE, get_book_emoji,
    get_paginated_books
)

mashqlar_router = Router()


# =====================================================
# 📌 FSM States
# =====================================================
class MashqStates(StatesGroup):
    practicing = State()
    ready_to_start = State()  # Yangi holat: so'zlar ko'rsatildi, mashq boshlashga tayyor


# =====================================================
# 📌 Practice specific functions
# =====================================================
def create_practice_books_kb(books: list, current_page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    """Mashq uchun lug'atlar klaviaturasi."""
    L = get_locale(lang)
    rows = []

    for book in books:
        emoji = get_book_emoji(book["is_public"], True)
        text = f"{emoji} {book['name']} ({book['word_count']})"
        callback = f"mashq:start:{book['id']}"
        rows.append([InlineKeyboardButton(text=text, callback_data=callback)])

    # Sahifalash tugmalari
    if total_pages > 1:
        nav_row = []
        if current_page > 0:
            nav_row.append(InlineKeyboardButton(text=L["prev_page"], callback_data=f"mashq:list:{current_page - 1}"))

        if current_page < total_pages - 1:
            nav_row.append(InlineKeyboardButton(text=L["next_page"], callback_data=f"mashq:list:{current_page + 1}"))

        if nav_row:
            rows.append(nav_row)

        # Sahifa ma'lumoti
        if total_pages > 1:
            page_info = L["page_info"].format(current=current_page + 1, total=total_pages)
            rows.append([InlineKeyboardButton(text=page_info, callback_data="noop")])

    rows.append([InlineKeyboardButton(text=L["back"], callback_data="cab:back")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def start_practice_kb(lang: str) -> InlineKeyboardMarkup:
    """Mashqni boshlash klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Mashqni boshlash", callback_data="mashq:begin_practice")],
        [InlineKeyboardButton(text=L["back"], callback_data="mashq:list")]
    ])


# =====================================================
# 📌 Handlers
# =====================================================

@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("mashq:list"))
async def cb_mashqlar(cb: CallbackQuery):
    """Mashq bo'limini ko'rsatish (sahifalangan)."""
    user_id = cb.from_user.id

    # Sahifa raqamini olish
    parts = cb.data.split(":")
    page = int(parts[2]) if len(parts) > 2 else 0

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    # Mashq uchun mos lug'atlarni olish (min_words=4 - mashq uchun yetarli so'z bo'lishi kerak)
    books, total_count = await get_paginated_books(user_id, page, BOOKS_PER_PAGE, min_words=4)

    if not books and page == 0:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📖 Lug'at yaratish", callback_data="lughat:new")],
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        text = "Mashq qilish uchun kamida 4 ta so'zi bo'lgan lug'at kerak.\n\nAvval lug'at yarating va so'z qo'shing."
        await safe_edit_or_send(cb, text, kb, lang)
        return

    if not books and page > 0:
        await cb.answer("Bu sahifada lug'at yo'q", show_alert=True)
        return

    total_pages = ceil(total_count / BOOKS_PER_PAGE)
    kb = create_practice_books_kb(books, page, total_pages, lang)

    header_text = f"🏋️ Mashq uchun lug'atlar ({total_count} ta)"
    if total_pages > 1:
        header_text += f"\n📄 {page + 1}/{total_pages} sahifa"

    await safe_edit_or_send(cb, header_text, kb, lang)
    await cb.answer()


@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("mashq:start:"))
async def cb_start_practice(cb: CallbackQuery, state: FSMContext):
    """Mashqni boshlash - avval so'zlarni ko'rsatish."""
    book_id = int(cb.data.split(":")[2])
    user_id = cb.from_user.id

    # Lug'atning mavjudligini va egasini tekshirish
    book_check = await db_exec(
        "SELECT name FROM vocab_books WHERE id=%s AND user_id=%s",
        (book_id, user_id), fetch=True
    )

    if not book_check:
        await cb.answer("Lug'at topilmadi yoki sizga tegishli emas!", show_alert=True)
        return

    rows = await db_exec(
        "SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s",
        (book_id,), fetch=True, many=True
    )

    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    if len(rows) < 4:
        await cb.answer("Bu lug'atda yetarli so'z yo'q (kamida 4 ta kerak)", show_alert=True)
        return

    # So'zlar ro'yxatini tayyorlash
    book_name = book_check["name"]
    words_list = []
    for idx, word in enumerate(rows, 1):
        words_list.append(f"{idx}. <b>{word['word_src']}</b> - {word['word_trg']}")
    
    words_text = f"📖 <b>{book_name}</b>\n"
    words_text += f"📊 Jami: {len(rows)} ta so'z\n\n"
    words_text += "\n".join(words_list)
    words_text += "\n\n💡 So'zlarni ko'rib chiqing va tayyor bo'lganingizda mashqni boshlang!"

    # So'zlarni state'ga saqlash
    random.shuffle(rows)
    await state.update_data(
        book_id=book_id,
        book_name=book_name,
        words=rows,
        index=0,
        correct=0,
        wrong=0,
        total=len(rows),
        answers=0,
        cycles=0,
        current_cycle_correct=0,
        current_cycle_wrong=0,
        cycles_stats=[]
    )
    await state.set_state(MashqStates.ready_to_start)
    
    await safe_edit_or_send(cb, words_text, start_practice_kb(lang), lang)
    await cb.answer()


@mashqlar_router.callback_query(lambda c: c.data == "mashq:begin_practice")
async def cb_begin_practice(cb: CallbackQuery, state: FSMContext):
    """Mashqni boshlash."""
    current_state = await state.get_state()
    if current_state != MashqStates.ready_to_start:
        await cb.answer("❌ Xato holat!", show_alert=True)
        return

    user_data = await get_user_data(cb.from_user.id)
    lang = user_data["lang"]

    await state.set_state(MashqStates.practicing)
    
    # Eski xabarni o'chirish
    try:
        await cb.message.delete()
    except:
        pass
    
    await send_next_question(cb.message, state, lang)
    await cb.answer()


async def send_next_question(msg: Message, state: FSMContext, lang: str):
    """Keyingi savolni yuborish."""
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
            words=words,
            index=0,
            cycles=cycles,
            cycles_stats=cycles_stats,
            current_cycle_correct=0,
            current_cycle_wrong=0
        )
        data = await state.get_data()
        index = 0

    current = data["words"][index]
    correct_answer = current["word_trg"]
    options = [correct_answer]
    seen = set(options)

    # Noto'g'ri variantlarni qo'shish
    while len(options) < 4 and len(options) < len(data["words"]):
        candidate = random.choice(data["words"])["word_trg"]
        if candidate not in seen:
            options.append(candidate)
            seen.add(candidate)

    random.shuffle(options)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
                            [InlineKeyboardButton(text=o, callback_data=f"ans:{index}:{o}")] for o in options] +
                        [
                            [InlineKeyboardButton(text=L["finish"], callback_data="mashq:finish")],
                            [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
                        ])

    # Progress va lug'at nomini ko'rsatish
    progress_text = f"📊 {data.get('correct', 0)}/{data.get('answers', 0)} to'g'ri"
    book_name = data.get('book_name', 'Lug\'at')
    question_text = f"📖 {book_name}\n{L['question'].format(word=current['word_src'])}\n\n{progress_text}"

    # Eski xabarni o'chirish va yangi yuborish
    try:
        await msg.delete()
    except:
        pass
    
    await msg.answer(question_text, reply_markup=kb)


@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    """Javobni tekshirish."""
    data = await state.get_data()
    _, idx_str, chosen = cb.data.split(":", 2)
    idx = int(idx_str)

    if idx >= len(data["words"]):
        await cb.answer("Xato", show_alert=True)
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


@mashqlar_router.callback_query(lambda c: c.data == "mashq:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    """Mashqni tugatish."""
    data = await state.get_data()
    total_unique = data.get("total", 0)
    total_answers = data.get("answers", 0)
    total_correct = data.get("correct", 0)
    total_wrong = data.get("wrong", 0)
    book_name = data.get("book_name", "Lug'at")
    cycles = data.get("cycles", 0)

    percent = (total_correct / total_answers * 100) if total_answers else 0.0

    user_data = await get_user_data(cb.from_user.id)
    L = get_locale(user_data["lang"])

    full_text = f"📖 {book_name}\n"
    full_text += f"{L['results_header']}\n\n"
    full_text += f"{L['results_lines'].format(unique=total_unique, answers=total_answers, correct=total_correct, wrong=total_wrong, percent=percent)}"

    # Tsikllar haqida ma'lumot
    if cycles > 0:
        full_text += f"\n🔄 Takrorlangan tsikllar: {cycles}"

    # Motivatsion xabar
    if percent >= 90:
        full_text += "\n\n🎉 Mukammal! Siz bu lug'atni juda yaxshi bilasiz!"
    elif percent >= 80:
        full_text += "\n\n⭐ Ajoyib natija! Davom eting!"
    elif percent >= 70:
        full_text += "\n\n👍 Yaxshi natija! Yanada yaxshilashga harakat qiling!"
    elif percent >= 50:
        full_text += "\n\n💪 Yomon emas! Yana mashq qiling!"
    else:
        full_text += "\n\n📚 Mashq davom eting, har gal yaxshilashasiz!"

    await state.clear()
    
    # Eski xabarni o'chirish
    try:
        await cb.message.delete()
    except:
        pass
    
    await cb.message.answer(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()