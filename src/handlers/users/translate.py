import os
import tempfile
import asyncio
from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor

from whisper import load_model
# import easyocr

from config import sql, db


executor = ThreadPoolExecutor()
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
    "tk": {"name": "Turkman", "flag": "🇹🇲"},
    "tg": {"name": "Tojik", "flag": "🇹🇯"},
}
OCR_LANGS = {
    "am": "amharic",
    "en": "english",
    "ru": "russian",
    "uz": "latin",     # yoki "cyrillic" agar o‘zbek kirill
    "tr": "turkish",
    "ar": "arabic",
    "fr": "french",
    "de": "german",
    "zh": "chinese_tra",  # yoki "chinese_simplified"
    "ja": "japanese",
    "ko": "korean",
    "hi": "hindi",
    "id": "indonesian",
    "fa": "persian",
    "es": "spanish",
    "it": "italian",
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
    """msg.answer() asosida uzun matnlarni yuborish"""
    chunk_size = 3500
    for i in range(0, len(text), chunk_size):
        await msg.answer(prefix + text[i:i + chunk_size], parse_mode="HTML")
        prefix = ""


async def answer_in_chunks_bot(bot: Bot, chat_id: int, text: str, prefix: str = ""):
    """bot.send_message() asosida uzun matnlarni yuborish"""
    chunk_size = 3500
    for i in range(0, len(text), chunk_size):
        await bot.send_message(chat_id, prefix + text[i:i + chunk_size], parse_mode="HTML")
        prefix = ""


@translate_router.message(Command("lang"))
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

    try:
        if msg.voice or msg.audio or msg.video_note:
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

    if msg.photo or msg.document:
        try:
            # Faylni olish
            file_id = msg.photo[-1].file_id if msg.photo else msg.document.file_id
            file = await msg.bot.get_file(file_id)
            file_bytes_io = await msg.bot.download(file.file_id, destination=BytesIO())
            image_bytes = file_bytes_io.getvalue()

            await msg.answer("🖼 Rasm qabul qilindi, matn ajratilmoqda...")

            text = extract_text_from_image(image_bytes, from_lang)

            if not text:
                await msg.answer("⚠️ Rasm ichida matn topilmadi.")
                return

            await answer_in_chunks(msg, text, prefix="📄 <b>Ajratilgan matn:</b>\n")

            translated = translate_auto(to_lang, text) if from_lang == "auto" else translate_text(from_lang, to_lang, text)
            await answer_in_chunks(msg, translated, prefix="🌐 <b>Tarjima:</b>\n")

        except Exception as e:
            await msg.answer(f"⚠️ Rasmni qayta ishlashda xatolik:\n{e}")


async def transcribe_audio_async(file_path: str) -> str:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(executor, lambda: model.transcribe(file_path))
    return result.get("text", "").strip()


async def process_audio_task(bot: Bot, chat_id: int, file_bytes: bytes, from_lang: str, to_lang: str, caption: str = None):
    try:
        processing_msg = await bot.send_message(chat_id, "⏳ Audio qayta ishlanmoqda, iltimos kuting...")

        # Caption tarjimasi
        if caption:
            try:
                cap_trans = (translate_auto(to_lang, caption) if from_lang == "auto"
                             else translate_text(from_lang, to_lang, caption))
                await bot.send_message(chat_id, f"📝 <b>Caption tarjimasi:</b>\n{cap_trans}", parse_mode="HTML")
            except Exception as e:
                await bot.send_message(chat_id, f"⚠️ Caption tarjima xatoligi: {e}")

        # Faylni vaqtincha saqlaymiz
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Transkripsiya
        transcript = await transcribe_audio_async(tmp_path)
        os.unlink(tmp_path)  # vaqtinchalik faylni o‘chirish

        if not transcript:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=processing_msg.message_id,
                    text="⚠️ Hech qanday matn aniqlanmadi."
                )
            except Exception:
                await bot.send_message(chat_id, "⚠️ Hech qanday matn aniqlanmadi.")
            return

        # Xabarni tahrirlash — muvaffaqiyatli
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=processing_msg.message_id,
                text="✅ Audio transkripsiya qilindi, tarjima qilinmoqda..."
            )
        except Exception:
            await bot.send_message(chat_id, "✅ Audio transkripsiya qilindi, tarjima qilinmoqda...")

        # Transkripsiya matni
        await answer_in_chunks_bot(bot, chat_id, transcript, prefix="🎙 <b>Transkripsiya:</b>\n")

        # Tarjimasi
        translated = (translate_auto(to_lang, transcript) if from_lang == "auto"
                      else translate_text(from_lang, to_lang, transcript))
        await answer_in_chunks_bot(bot, chat_id, translated, prefix="🌐 <b>Tarjima:</b>\n")

        # Ortiqcha xabarni o‘chirish
        try:
            await bot.delete_message(chat_id, processing_msg.message_id)
        except Exception:
            pass

    except Exception as e:
        await bot.send_message(chat_id, f"⚠️ Xatolik yuz berdi:\n{e}")


from aiogram import Bot

@translate_router.message(F.voice | F.audio | F.video_note)
async def handle_media(msg: Message, bot: Bot):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.answer("❗ Chiquvchi til tanlanmagan.")
        return

    try:
        if msg.voice:
            file_id = msg.voice.file_id
        elif msg.audio:
            file_id = msg.audio.file_id
        else:
            file_id = msg.video_note.file_id

        file = await bot.get_file(file_id)
        file_bytes = await bot.download(file.file_id, destination=BytesIO())

        asyncio.create_task(process_audio_task(
            bot,
            msg.chat.id,
            file_bytes.getvalue(),
            from_lang or "auto",
            to_lang,
            caption=msg.caption
        ))

    except Exception as e:
        await msg.answer(f"⚠️ Foylni yuklashda xatolik:\n{e}")

# async def process_image_task(bot: Bot, chat_id: int, image_bytes: bytes, from_lang: str, to_lang: str):
#     try:
#         if from_lang not in OCR_LANGS:
#             await bot.send_message(chat_id, "⚠️ Bu tilda OCR (rasmdan matn ajratish) hozircha qo‘llab-quvvatlanmaydi.")
#             return
#
#         processing_msg = await bot.send_message(chat_id, "⏳ Rasm qayta ishlanmoqda, iltimos kuting...")
#
#         text = extract_text_from_image(image_bytes, from_lang)
#
#         if not text:
#             await bot.edit_message_text(
#                 chat_id=chat_id,
#                 message_id=processing_msg.message_id,
#                 text="⚠️ Rasm ichida matn topilmadi."
#             )
#             return
#
#         await bot.edit_message_text(
#             chat_id=chat_id,
#             message_id=processing_msg.message_id,
#             text="✅ Rasmdan matn ajratildi, tarjima qilinmoqda..."
#         )
#
#         await answer_in_chunks_bot(bot, chat_id, text, prefix="📄 <b>Ajratilgan matn:</b>\n")
#
#         translated = (
#             translate_auto(to_lang, text) if from_lang == "auto"
#             else translate_text(from_lang, to_lang, text)
#         )
#         await answer_in_chunks_bot(bot, chat_id, translated, prefix="🌐 <b>Tarjima:</b>\n")
#
#         # Oxirida qayta ishlash xabarini o‘chirish
#         try:
#             await bot.delete_message(chat_id, processing_msg.message_id)
#         except Exception:
#             pass
#
#     except Exception as e:
#         await bot.send_message(chat_id, f"⚠️ Rasmni qayta ishlashda xatolik:\n{e}")
#
# def extract_text_from_image(image_bytes: bytes, lang_code: str) -> str:
#     if lang_code not in OCR_LANGS:
#         return None  # bu holda foydalanuvchiga "til qo‘llab-quvvatlanmaydi" deb aytiladi
#
#     reader = easyocr.Reader([lang_code], gpu=False)
#     result = reader.readtext(image_bytes, detail=0)
#     return "\n".join(result).strip()
#
# @translate_router.message(F.photo | F.document)
# async def handle_image(msg: Message):
#     user_langs = get_user_langs(msg.from_user.id)
#     if not user_langs:
#         await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
#         return
#
#     from_lang, to_lang = user_langs
#     if not to_lang:
#         await msg.answer("❗ Chiquvchi til tanlanmagan.")
#         return
#
#     try:
#         # Faylni olish
#         file_id = msg.photo[-1].file_id if msg.photo else msg.document.file_id
#         file = await msg.bot.get_file(file_id)
#         file_bytes_io = await msg.bot.download(file.file_id, destination=BytesIO())
#         image_bytes = file_bytes_io.getvalue()
#
#         # Orqa fon vazifa
#         asyncio.create_task(
#             process_image_task(
#                 msg.bot,
#                 msg.chat.id,
#                 image_bytes,
#                 from_lang or "auto",
#                 to_lang
#             )
#         )
#
#         await msg.answer("🖼 Rasm qabul qilindi, qayta ishlash boshlanmoqda...")
#
#     except Exception as e:
#         await msg.answer(f"⚠️ Rasmni yuklashda xatolik:\n{e}")
