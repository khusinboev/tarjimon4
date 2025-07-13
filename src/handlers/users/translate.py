from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from deep_translator import GoogleTranslator

from src.handlers.users.xususiyatlar import get_language_inline_keyboard, update_user_lang, get_user_langs, \
    translate_auto, translate_text

translate_router = Router()


# --- TILLAR BUYRUG‘I ---

@translate_router.message(Command("languages"))
async def language_menu_handler(msg: Message):
    kb = get_language_inline_keyboard(msg.from_user.id)
    await msg.answer("🔤 Tillarni tanlang:\nChap: Kiruvchi | O‘ng: Chiquvchi", reply_markup=kb)

@translate_router.callback_query(F.data.startswith("setlang:"))
async def process_language_selection(callback: CallbackQuery):
    _, direction, lang_code = callback.data.split(":")
    update_user_lang(callback.from_user.id, lang_code, direction)
    kb = get_language_inline_keyboard(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("✅ Til yangilandi")

# --- TEXT TARJIMA HANDLER ---

@translate_router.message(F.text)
async def handle_text(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.answer("❗ Chiquvchi til tanlanmagan.")
        return

    if from_lang == "auto" or not from_lang:
        result = translate_auto(to_lang, msg.text)
    else:
        result = translate_text(from_lang, to_lang, msg.text)

    try:
        await msg.reply(result)
    except:
        await msg.answer(result)

# --- CAPTION TARJIMA HANDLER ---

@translate_router.message(F.caption)
async def handle_caption(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        return

    if from_lang == "auto" or not from_lang:
        result = translate_auto(to_lang, msg.caption)
    else:
        result = translate_text(from_lang, to_lang, msg.caption)
    try:
        await msg.reply(result)
    except:
        await msg.answer(result)
