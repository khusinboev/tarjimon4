import tempfile
import os

from aiogram import Router, F
from aiogram.types import Message
from whisper import load_model
from deep_translator import GoogleTranslator

from src.handlers.users.xususiyatlar import get_user_langs

media_router = Router()

# Whisper modelini bitta marta yuklaymiz
model = load_model("tiny")

# --- FUNKSIYA: AUDIO faylni transkriptsiya qilib, tarjima qilish ---
async def transcribe_and_translate(file: bytes, to_lang: str, from_lang: str = "auto") -> str:
    try:
        # 1. Faylni vaqtinchalik saqlash
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(file)
            tmp_path = tmp.name

        # 2. Whisper orqali transkriptsiya
        result = model.transcribe(tmp_path)
        text = result["text"]

        # 3. Tarjima
        translated = GoogleTranslator(source=from_lang, target=to_lang).translate(text)

        return f"🎙 <b>Transkripsiya:</b> {text}\n\n🌐 <b>Tarjima:</b> {translated}"
    except Exception as e:
        return f"⚠️ Xatolik: {e}"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# --- HANDLER: VOICE ---
@media_router.message(F.voice)
async def handle_voice(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.reply("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.reply("❗ Chiquvchi til tanlanmagan.")
        return

    file = await msg.bot.download(msg.voice.file_id)
    content = file.read()
    result = await transcribe_and_translate(content, to_lang, from_lang or "auto")
    await msg.reply(result)


# --- HANDLER: AUDIO ---
@media_router.message(F.audio)
async def handle_audio(msg: Message):
    user_langs = get_user_langs(msg.from_user.id)
    if not user_langs:
        await msg.reply("❗ Avval /languages buyrug‘i orqali tillarni tanlang.")
        return

    from_lang, to_lang = user_langs
    if not to_lang:
        await msg.reply("❗ Chiquvchi til tanlanmagan.")
        return

    file = await msg.bot.download(msg.audio.file_id)
    content = file.read()
    result = await transcribe_and_translate(content, to_lang, from_lang or "auto")
    await msg.reply(result)
