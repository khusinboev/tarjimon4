import os
import tempfile

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, 
    CallbackQuery, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup
)
from deep_translator import GoogleTranslator
from whisper import load_model

from config import sql, db

# Yagona router
translate_router = Router()

# --- Tillar ro‘yxati ---
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
    "fa": {"name": "Fors (Afg‘on)", "flag": "🇮🇷"},
    "es": {"name": "Ispan", "flag": "🇪🇸"},
    "it": {"name": "Italyan", "flag": "🇮🇹"},
    "kk": {"name": "Qozoq", "flag": "🇰🇿"},
    "ky": {"name": "Qirg‘iz", "flag": "🇰🇬"},
    "az": {"name": "Ozarbayjon", "flag": "🇦🇿"},
    "tk": {"name": "Turkman", "flag": "🇹🇰"},
    "tg": {"name": "Tojik", "flag": "🇹🇯"},
}

# --- Foydalanuvchi tillari bilan ishlovchi funksiyalar ---
def get_user_langs(user_id: int):
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id = %s", (user_id,))
    return sql.fetchone()

def update_user_lang(user_id: int, lang_code: str, direction: str):
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

# --- Tarjima funksiyalari ---
def translate_text(from_lang: str, to_lang: str, text: str) -> str:
    try:
        return GoogleTranslator(source=from_lang, target=to_lang).translate(text)
    except Exception as e:
        return f"⚠️ Tarjima xatosi: {e}"

def translate_auto(to_lang: str, text: str) -> str:
    return translate_text("auto", to_lang, text)

# --- Komanda: /languages ---
@translate_router.message(Command("languages"))
async def language_menu_handler(msg: Message):
    kb = get_language_inline_keyboard(msg.from_user.id)
    await msg.answer("🌤 Tillarni tanlang:\nChap: Kiruvchi | O‘ng: Chiquvchi", reply_markup=kb)

# --- Tugma orqali tilni tanlash ---
@translate_router.callback_query(F.data.startswith("setlang:"))
async def process_language_selection(callback: CallbackQuery):
    _, direction, lang_code = callback.data.split(":")
    update_user_lang(callback.from_user.id, lang_code, direction)
    kb = get_language_inline_keyboard(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer("✅ Til yangilandi")

# --- Matnni tarjima qilish ---
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

    try:
        if from_lang == "auto" or not from_lang:
            result = translate_auto(to_lang, msg.text)
        else:
            result = translate_text(from_lang, to_lang, msg.text)

        await msg.reply(result[:3500] + ("..." if len(result) > 3500 else ""), parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"⚠️ Xatolik yuz berdi:\n{e}")

# --- Caption (sarlavha)ni tarjima qilish ---
@translate_router.message(F.caption)
async def handle_caption(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        return

    try:
        if from_lang == "auto" or not from_lang:
            result = translate_auto(to_lang, msg.caption)
        else:
            result = translate_text(from_lang, to_lang, msg.caption)

        await msg.reply(result[:3500] + ("..." if len(result) > 3500 else ""), parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"⚠️ Xatolik yuz berdi:\n{e}")

# --- Whisper model faqat bir marta yuklanadi ---
model = load_model("tiny")

def limit_text_length(text: str, max_len: int = 3500) -> str:
    return text if len(text) <= max_len else text[:max_len] + "..."

# --- Ovozni transkriptsiya va tarjima qilish ---
async def transcribe_and_translate(file_bytes: bytes, to_lang: str, from_lang: str = "auto") -> str:
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        result = model.transcribe(tmp_path)
        text = result.get("text", "").strip()

        if not text:
            return "⚠️ Hech qanday matn aniqlanmadi."

        translated = GoogleTranslator(source=from_lang, target=to_lang).translate(text)

        return limit_text_length(
            f"🎙 <b>Transkripsiya:</b> {text}\n\n🌐 <b>Tarjima:</b> {translated}"
        )
    except Exception as e:
        return f"⚠️ Xatolik: {e}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Voice va Audio xabarlar uchun handler ---
@translate_router.message(F.voice | F.audio)
async def handle_media(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.answer("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.answer("❗ Chiquvchi til tanlanmagan.")
        return

    try:
        file_obj = await msg.bot.download(msg.voice.file_id if msg.voice else msg.audio.file_id)
        file_bytes = file_obj.read()

        result = await transcribe_and_translate(file_bytes, to_lang, from_lang or "auto")
        await msg.reply(result, parse_mode="HTML")
    except Exception as e:
        await msg.reply(f"⚠️ Xatolik yuz berdi:\n{e}")