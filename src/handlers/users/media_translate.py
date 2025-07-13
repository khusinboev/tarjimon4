import os
import tempfile

from aiogram import Router, F
from aiogram.types import Message
from whisper import load_model
from deep_translator import GoogleTranslator

from src.handlers.users.xususiyatlar import get_user_langs

media_router = Router()

# Whisper modelini faqat bir marta yuklaymiz
model = load_model("tiny")

# --- LIMITER ---
def limit_text_length(text: str, max_len: int = 3500) -> str:
    """Uzoq matnni qisqartiradi."""
    return text if len(text) <= max_len else text[:max_len] + "..."

# --- AUDIO faylni transkriptsiya va tarjima qilish ---
async def transcribe_and_translate(file_bytes: bytes, to_lang: str, from_lang: str = "auto") -> str:
    tmp_path = None
    try:
        # Faylni vaqtincha yozish
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # Whisper orqali matn olish
        result = model.transcribe(tmp_path)
        text = result.get("text", "").strip()

        if not text:
            return "⚠️ Hech qanday matn aniqlanmadi."

        # Tarjima
        translated = GoogleTranslator(source=from_lang, target=to_lang).translate(text)

        return limit_text_length(
            f"🎙 <b>Transkripsiya:</b> {text}\n\n🌐 <b>Tarjima:</b> {translated}"
        )
    except Exception as e:
        return f"⚠️ Xatolik: {e}"
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Universal handler: Voice va Audio ---
@media_router.message(F.voice | F.audio)
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
