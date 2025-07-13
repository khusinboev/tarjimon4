import os
import tempfile
import asyncio
from io import BytesIO

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from deep_translator import GoogleTranslator
from whisper import load_model

from config import sql, db

translate_router = Router()
model = load_model("tiny")

LANGUAGES = {
    "auto": {"name": "Avto", "flag": "🌐"},
    "uz": {"name": "O‘zbek", "flag": "🇺🇿"},
    "en": {"name": "Ingliz", "flag": "🇬🇧"},
    "ru": {"name": "Rus", "flag": "🇷🇺"},
    "tr": {"name": "Turk", "flag": "🇹🇷"},
    "ar": {"name": "Arab", "flag": "🇸🇦"},
    "fr": {"name": "Fransuz", "flag": "🇫🇷"},
    "de": {"name": "Nemis", "flag": "🇩🇪"},
    "zh": {"name": "Xitoy", "flag": "🇨🇳"},
    "ja": {"name": "Yapon", "flag": "🇯🇵"},
    "ko": {"name": "Koreys", "flag": "🇰🇷"},
    "hi": {"name": "Hind", "flag": "🇮🇳"},
    "id": {"name": "Indonez", "flag": "🇮🇩"},
    "fa": {"name": "Fors", "flag": "🇮🇷"},
    "es": {"name": "Ispan", "flag": "🇪🇸"},
    "it": {"name": "Italyan", "flag": "🇮🇹"},
    "kk": {"name": "Qozoq", "flag": "🇰🇿"},
    "ky": {"name": "Qirg'iz", "flag": "🇰🇬"},
    "az": {"name": "Ozarbayjon", "flag": "🇦🇿"},
    "tk": {"name": "Turkman", "flag": "🇹🇰"},
    "tg": {"name": "Tojik", "flag": "🇹🇯"},
}


def get_user_langs(user_id: int):
    """Foydalanuvchi tanlagan tillarni olish"""
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    return sql.fetchone()


def update_user_lang(user_id: int, lang_code: str, direction: str):
    """Foydalanuvchi tilini yangilash"""
    assert direction in ["from", "to"]
    field = "from_lang" if direction == "from" else "to_lang"

    sql.execute("SELECT 1 FROM user_languages WHERE user_id = %s", (user_id,))
    if sql.fetchone():
        sql.execute(f"UPDATE user_languages SET {field} = %s WHERE user_id = %s", (lang_code, user_id))
    else:
        from_lang = lang_code if direction == "from" else None
        to_lang = lang_code if direction == "to" else None
        sql.execute(
            "INSERT INTO user_languages (user_id, from_lang, to_lang) VALUES (%s, %s, %s)",
            (user_id, from_lang, to_lang),
        )
    db.commit()


def get_language_inline_keyboard(user_id: int):
    """Tillar uchun inline keyboard yaratish"""
    user_langs = get_user_langs(user_id) or (None, None)
    from_lang, to_lang = user_langs

    buttons = [[
        InlineKeyboardButton(
            text=f"✅ 🌐 Auto" if from_lang == "auto" else "🌐 Auto",
            callback_data="setlang:from:auto",
        ),
        InlineKeyboardButton(text=" ", callback_data="ignore"),
    ]]

    for code, data in LANGUAGES.items():
        if code == "auto":
            continue
        from_text = f"✅ {data['flag']} {data['name']}" if code == from_lang else f"{data['flag']} {data['name']}"
        to_text = f"✅ {data['flag']} {data['name']}" if code == to_lang else f"{data['flag']} {data['name']}"
        buttons.append([
            InlineKeyboardButton(text=from_text, callback_data=f"setlang:from:{code}"),
            InlineKeyboardButton(text=to_text, callback_data=f"setlang:to:{code}"),
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def translate_text(from_lang: str, to_lang: str, text: str) -> str:
    """Matnni tarjima qilish"""
    try:
        return GoogleTranslator(source=from_lang, target=to_lang).translate(text)
    except Exception as e:
        return f"⚠️ Tarjima xatosi: {e}"


def translate_auto(to_lang: str, text: str) -> str:
    """Avto tarjima"""
    return translate_text("auto", to_lang, text)


async def answer_in_chunks(msg: Message, text: str, prefix: str = ""):
    """Uzun matnlarni bo'laklarga bo'lib jo'natish"""
    chunk_size = 3500
    for i in range(0, len(text), chunk_size):
        await msg.answer(prefix + text[i:i + chunk_size], parse_mode="HTML")
        prefix = ""


@translate_router.message(Command("languages"))
async def language_menu_handler(msg: Message):
    """Til menyusini ko'rsatish"""
    kb = get_language_inline_keyboard(msg.from_user.id)
    await msg.answer("🌤 Tillarni tanlang:\nChap: Kiruvchi | O‘ng: Chiquvchi", reply_markup=kb)


@translate_router.callback_query(F.data.startswith("setlang:"))
async def process_language_selection(callback: CallbackQuery):
    """Til tanlashni qayta ishlash"""
    _, direction, lang_code = callback.data.split(":")
    update_user_lang(callback.from_user.id, lang_code, direction)
    kb = get_language_inline_keyboard(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("✅ Til yangilandi")


@translate_router.message(F.text)
async def handle_text(msg: Message):
    """Matnli xabarlarni qayta ishlash"""
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.answer("❗ Chiquvchi til tanlanmagan.")
        return

    try:
        result = translate_auto(to_lang, msg.text) if from_lang == "auto" else translate_text(from_lang, to_lang, msg.text)
        await answer_in_chunks(msg, result)
    except Exception as e:
        await msg.answer(f"⚠️ Xatolik yuz berdi:\n{e}")


@translate_router.message(F.caption)
async def handle_caption(msg: Message):
    """Rasmlar uchun captionlarni qayta ishlash"""
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        return

    try:
        result = translate_auto(to_lang, msg.caption) if from_lang == "auto" else translate_text(from_lang, to_lang, msg.caption)
        await answer_in_chunks(msg, result)
    except Exception as e:
        await msg.answer(f"⚠️ Xatolik yuz berdi:\n{e}")


async def transcribe_audio(file_bytes: bytes) -> str:
    """Audioni matnga aylantirish (transkripsiya qilish)"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg") as tmp:
            tmp.write(file_bytes)
            tmp.flush()  # Ma'lumotlarni diskga yozishni ta'minlash
            result = model.transcribe(tmp.name)
            return result.get("text", "").strip()
    except Exception as e:
        return f"⚠️ Transkripsiya xatosi: {e}"


async def process_audio_task(msg: Message, file_bytes: bytes, from_lang: str, to_lang: str, caption: str = None):
    """Audioni orqa fonda qayta ishlash"""
    try:
        # Jarayon boshlanganligi haqida xabar
        processing_msg = await msg.answer("⏳ Audio qayta ishlanmoqda, iltimos kuting...")

        # Agar caption bo'lsa, avval uni tarjima qilish
        if caption:
            try:
                cap_trans = (translate_auto(to_lang, caption) if from_lang == "auto" 
                          else translate_text(from_lang, to_lang, caption))
                await answer_in_chunks(msg, cap_trans, prefix="📝 <b>Caption tarjimasi:</b>\n")
            except Exception as e:
                await msg.answer(f"⚠️ Caption tarjima xatoligi: {e}")

        # Transkripsiya qilish
        transcript = await transcribe_audio(file_bytes)
        if not transcript:
            await processing_msg.edit_text("⚠️ Hech qanday matn aniqlanmadi.")
            return

        await processing_msg.edit_text("✅ Audio transkripsiya qilindi, tarjima qilinmoqda...")
        await answer_in_chunks(msg, transcript, prefix="🎙 <b>Transkripsiya:</b>\n")

        # Tarjima qilish
        try:
            translated = (translate_auto(to_lang, transcript) if from_lang == "auto" 
                        else translate_text(from_lang, to_lang, transcript))
            await answer_in_chunks(msg, translated, prefix="🌐 <b>Tarjima:</b>\n")
            await processing_msg.delete()  # Jarayon tugaganligi haqidagi xabarni o'chirish
        except Exception as e:
            await processing_msg.edit_text(f"⚠️ Tarjima xatoligi: {e}")

    except Exception as e:
        error_msg = f"⚠️ Xatolik yuz berdi: {str(e)}"
        if 'processing_msg' in locals():
            await processing_msg.edit_text(error_msg)
        else:
            await msg.answer(error_msg)


@translate_router.message(F.voice | F.audio | F.video_note)
async def handle_media(msg: Message):
    """Audio fayllarni qayta ishlash"""
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.answer("❗ Chiquvchi til tanlanmagan.")
        return

    try:
        # Faylni yuklab olish
        if msg.voice:
            file_id = msg.voice.file_id
        elif msg.audio:
            file_id = msg.audio.file_id
        else:  # video_note
            file_id = msg.video_note.file_id

        file = await msg.bot.get_file(file_id)
        file_bytes = await msg.bot.download(file.file_id, destination=BytesIO())

        # Orqa fonda ishlash uchun task yaratish
        asyncio.create_task(
            process_audio_task(
                msg, 
                file_bytes.getvalue(), 
                from_lang or "auto", 
                to_lang, 
                caption=msg.caption
            )
        )

        # Darhol javob qaytarish
        await msg.answer("🔊 Audio qabul qilindi, qayta ishlash boshlandi...")

    except Exception as e:
        await msg.answer(f"⚠️ Foydani yuklashda xatolik:\n{e}")