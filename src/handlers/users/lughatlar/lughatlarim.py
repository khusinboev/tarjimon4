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
from src.handlers.users.lughatlar.vocabs import get_user_data, get_locale, cabinet_kb, books_kb, get_book_details, \
    VocabStates, db_exec, export_book_to_excel, book_kb

lughatlarim_router = Router()

@lughatlarim_router.callback_query(lambda c: c.data == "cab:books")
async def cb_my_books(cb: CallbackQuery):
    data = await get_user_data(cb.from_user.id)
    L = get_locale(data["lang"])
    if not data["books"]:
        await cb.message.edit_text(L["no_books"], reply_markup=cabinet_kb(data["lang"]))
    else:
        await cb.message.edit_text(L["my_books"], reply_markup=books_kb(data["books"], data["lang"]))
    await cb.answer()

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("book:"))
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
                               reply_markup=books_kb(book_id, data["lang"], book["is_public"], is_owner))
    await cb.answer()

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("book:add:"))
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

@lughatlarim_router.message(VocabStates.waiting_word_list)
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

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("book:delete:"))
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

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("book:confirm_delete:"))
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

@lughatlarim_router.callback_query(lambda c: c.data and c.data.startswith("book:export:"))
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
                               reply_markup=book_kb(book_id=book_id, is_public=book["is_public"], is_owner=book["user_id"] == cb.from_user.id, lang=str(L)))
    await cb.answer()

@lughatlarim_router.callback_query(lambda c: c.data == "cab:new")
async def cb_new_book(cb: CallbackQuery, state: FSMContext):
    L = get_locale((await get_user_data(cb.from_user.id))["lang"])
    await cb.message.edit_text(L["enter_book_name"], reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=L["cancel"], callback_data="cab:books")]]
    ))
    await state.set_state(VocabStates.waiting_book_name)
    await cb.answer()

@lughatlarim_router.message(VocabStates.waiting_book_name)
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