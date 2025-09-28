from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import random

from src.handlers.users.lughatlar.vocabs import (
    get_user_data, db_exec, get_locale, two_col_rows,
    safe_edit_or_send, cabinet_kb
)

mashqlar_router = Router()


# =====================================================
# 🔌 FSM States
# =====================================================
class MashqStates(StatesGroup):
    practicing = State()


# =====================================================
# 🔌 UI Builders
# =====================================================
def practice_books_kb(books, lang: str) -> InlineKeyboardMarkup:
    """Mashq uchun lug'atlar ro'yxati klaviaturasi."""
    L = get_locale(lang)
    btns = []
    for b in books:
        btns.append(InlineKeyboardButton(text=b["name"], callback_data=f"mashq:start:{b['id']}"))

    btns.append(InlineKeyboardButton(text=L["back"], callback_data="cab:back"))
    return InlineKeyboardMarkup(inline_keyboard=two_col_rows(btns))


# =====================================================
# 🔌 Handlers
# =====================================================

@mashqlar_router.callback_query(lambda c: c.data == "mashq:list")
async def cb_mashqlar(cb: CallbackQuery):
    """Mashq bo'limini ko'rsatish."""
    user_id = cb.from_user.id
    data = await get_user_data(user_id)
    lang, books = data["lang"], data["books"]
    L = get_locale(lang)

    if not books:
        await cb.answer(L["no_books"], show_alert=True)
        return

    await safe_edit_or_send(cb, "🏋️ " + L["practice"], practice_books_kb(books, lang), lang)
    await cb.answer()


@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("mashq:start:"))
async def cb_start_practice(cb: CallbackQuery, state: FSMContext):
    """Mashqni boshlash."""
    book_id = int(cb.data.split(":")[2])
    rows = await db_exec("SELECT word_src, word_trg FROM vocab_entries WHERE book_id=%s", (book_id,), fetch=True,
                         many=True)

    data = await get_user_data(cb.from_user.id)
    lang = data["lang"]
    L = get_locale(lang)

    if len(rows) < 4:
        await cb.answer("❌ " + L["empty_book"], show_alert=True)
        return

    random.shuffle(rows)
    await state.update_data(
        book_id=book_id, words=rows, index=0, correct=0, wrong=0, total=len(rows),
        answers=0, cycles=0, current_cycle_correct=0, current_cycle_wrong=0, cycles_stats=[]
    )
    await state.set_state(MashqStates.practicing)
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
                                                  [InlineKeyboardButton(text=o, callback_data=f"ans:{index}:{o}")] for o
                                                  in options
                                              ] + [
                                                  [InlineKeyboardButton(text=L["finish"],
                                                                        callback_data="mashq:finish")],
                                                  [InlineKeyboardButton(text=L["main_menu"], callback_data="cab:back")]
                                              ])

    await msg.edit_text(L["question"].format(word=current["word_src"]), reply_markup=kb)


@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
async def cb_practice_answer(cb: CallbackQuery, state: FSMContext):
    """Javobni tekshirish."""
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


@mashqlar_router.callback_query(lambda c: c.data == "mashq:finish")
async def cb_practice_finish(cb: CallbackQuery, state: FSMContext):
    """Mashqni tugatish."""
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