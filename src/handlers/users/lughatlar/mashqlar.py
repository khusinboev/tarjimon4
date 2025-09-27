import asyncio
import random
import os
from typing import List, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import db
from src.handlers.users.lughatlar.vocabs import get_user_data, get_locale, db_exec, books_kb, cabinet_kb, VocabStates

mashqlar_router = Router()

# =====================================================
# 📌 Practice
# =====================================================
@mashqlar_router.callback_query(lambda c: c.data == "cab:practice")
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

@mashqlar_router.callback_query(lambda c: c.data and (c.data.startswith("practice_book:") or c.data.startswith("book:practice:")))
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

@mashqlar_router.callback_query(lambda c: c.data and c.data.startswith("ans:"))
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

@mashqlar_router.callback_query(lambda c: c.data == "practice:finish")
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
