from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, cabinet_kb
)

ommaviylar_router = Router()


# =====================================================
# 🔌 FSM States
# =====================================================
class OmmaviyMashqStates(StatesGroup):
    practicing = State()


# =====================================================
# 🔌 UI Builders
# =====================================================
def public_books_kb(books, lang: str) -> InlineKeyboardMarkup:
    """Ommaviy lug'atlar ro'yxati klaviaturasi."""
    L = get_locale(lang)
    btns = []
    for b in books:
        # Muallif nomini qo'shish
        author_name = b.get("author_name", "Noma'lum")
        text = f"📖 {b['name']}\n👤 {author_name}"
        btns.append(InlineKeyboardButton(text=b["name"], callback_data=f"ommaviy:info:{b['id']}"))

    btns.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back"))
    return InlineKeyboardMarkup(inline_keyboard=two_col_rows(btns))


def public_book_detail_kb(book_id: int, lang: str) -> InlineKeyboardMarkup:
    """Ommaviy lug'at batafsil sahifasi klaviaturasi."""
    L = get_locale(lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶ Mashq boshlash", callback_data=f"ommaviy:start:{book_id}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="ommaviy:list")]
    ])


# =====================================================
# 🔌 Handlers
# =====================================================

@ommaviylar_router.callback_query(lambda c: c.data == "ommaviy:list")
async def cb_ommaviylar(cb: CallbackQuery):
    """Ommaviy lug'atlar bo'limini ko'rsatish."""
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang = data["lang"]
    L = get_locale(lang)

    # Ommaviy lug'atlarni olish (o'z lug'atlarini chiqarib tashlash)
    public_books = await db_exec("""
                                 SELECT vb.id,
                                        vb.name,
                                        vb.description,
                                        a.user_id                              as author_id,
                                        COALESCE(a.user_id::text, 'Noma''lum') as author_name,
                                        COUNT(ve.id)                           as word_count
                                 FROM vocab_books vb
                                          LEFT JOIN accounts a ON vb.user_id = a.user_id
                                          LEFT JOIN vocab_entries ve ON vb.id = ve.book_id
                                 WHERE vb.is_public = TRUE
                                   AND vb.user_id != %s
                                 GROUP BY vb.id, vb.name, vb.description, a.user_id
                                 HAVING COUNT (ve.id) >= 4
                                 ORDER BY vb.created_at DESC
                                 """, (user_id,), fetch=True, many=True)

    if not public_books:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L["back"], callback_data="cab:back")]
        ])
        await safe_edit_or_send(cb, "🌐 Hozircha ommaviy lug'atlar yo'q.", kb, lang)
        return

    await safe_edit_or_send(cb, "🌐 Ommaviy lug'atlar", public_books_kb(public_books, lang), lang)
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
                                     a.user_id    as author_id,
                                     COUNT(ve.id) as word_count,
                                     vb.created_at::date as created_date
                              FROM vocab_books vb
                                       LEFT JOIN accounts a ON vb.user_id = a.user_id
                                       LEFT JOIN vocab_entries ve ON vb.id = ve.book_id
                              WHERE vb.id = %s
                                AND vb.is_public = TRUE
                                AND vb.user_id != %s
                              GROUP BY vb.id, vb.name, vb.description, a.user_id, vb.created_at
                              """, (book_id, user_id), fetch=True)

    if not book_info:
        await cb.answer("❌ Lug'at topilmadi!", show_alert=True)
        return

    data = await get_user_data(user_id)
    lang = data["lang"]

    text = f"📖 {book_info['name']}\n"
    text += f"👤 Muallif: ID {book_info['author_id']}\n"
    text += f"📊 So'zlar soni: {book_info['word_count']}\n"
    text += f"📅 Yaratilgan: {book_info['created_date']}\n"
    if book_info['description']:
        text += f"📝 Tavsif: {book_info['description']}"

    await safe_edit_or_send(cb, text, public_book_detail_kb(book_id, lang), lang)
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
                           AND vb.user_id != %s
                         """, (book_id, user_id), fetch=True, many=True)

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

    await msg.edit_text(L["question"].format(word=current["word_src"]), reply_markup=kb)


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

    await state.clear()
    await cb.message.edit_text(full_text)
    await cb.message.answer(L["cabinet"], reply_markup=cabinet_kb(user_data["lang"]))
    await cb.answer()