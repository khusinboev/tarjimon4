import asyncio
import random
import os
from typing import List, Dict, Any

from aiogram import Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from config import db
from src.handlers.users.lughatlar.vocabs import get_user_data, get_locale, db_exec, cabinet_kb, get_book_details, \
    book_kb, two_col_rows, books_kb

ommaviylar_router = Router()


@ommaviylar_router.callback_query(lambda c: c.data == "cab:public_books")
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

@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("public_book:"))
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
                               reply_markup=book_kb(book_id, data["lang"], is_public=True, is_owner=is_owner))
    await cb.answer()

@ommaviylar_router.callback_query(lambda c: c.data and c.data.startswith("book:toggle_public:"))
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
