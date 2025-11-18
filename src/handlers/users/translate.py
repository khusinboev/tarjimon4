import asyncio
import random
from io import BytesIO
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from deep_translator import GoogleTranslator
from googletrans import Translator as GoogleTransFallback  # pip install googletrans==4.0.0-rc1

from config import sql, db, bot, ADMIN_ID, LANGUAGES
from src.keyboards.buttons import UserPanels
from src.keyboards.keyboard_func import CheckData

translate_router = Router()


fallback_translator = GoogleTransFallback()

# --- Database helpers ---
def get_user_langs(user_id: int):
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id=%s", (user_id,))
    return sql.fetchone()

def update_user_lang(user_id: int, lang_code: str, direction: str):
    field = "from_lang" if direction == "from" else "to_lang"
    sql.execute("SELECT 1 FROM user_languages WHERE user_id=%s", (user_id,))
    if sql.fetchone():
        sql.execute(f"UPDATE user_languages SET {field}=%s WHERE user_id=%s", (lang_code, user_id))
    else:
        from_lang = lang_code if direction == "from" else None
        to_lang = lang_code if direction == "to" else None
        sql.execute(
            "INSERT INTO user_languages (user_id, from_lang, to_lang) VALUES (%s, %s, %s)",
            (user_id, from_lang, to_lang),
        )
    db.commit()

# --- UI helpers ---
def get_language_keyboard(user_id: int):
    from_lang, to_lang = get_user_langs(user_id) or (None, None)
    buttons = [[
        InlineKeyboardButton(
            text=f"{'✅ ' if from_lang == 'auto' else ''}🌐 Auto",
            callback_data="setlang:from:auto"
        ),
        InlineKeyboardButton(text=" ", callback_data="setlang:ignore")
    ]]
    for code, data in LANGUAGES.items():
        if code == "auto": continue
        buttons.append([
            InlineKeyboardButton(
                text=f"{'✅ ' if from_lang == code else ''}{data['flag']} {data['name']}",
                callback_data=f"setlang:from:{code}"
            ),
            InlineKeyboardButton(
                text=f"{'✅ ' if to_lang == code else ''}{data['flag']} {data['name']}",
                callback_data=f"setlang:to:{code}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_translation_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌐 Langs", callback_data="translate:setlang"),
                InlineKeyboardButton(text="🔄 Switch", callback_data="translate:switch")
            ]
        ]
    )

# --- Translation with fallback ---
def translate_text(from_lang: str, to_lang: str, text: str):
    try:
        # Asosiy tarjimon
        return GoogleTranslator(source=from_lang, target=to_lang).translate(text)
    except Exception:
        try:
            # Fallback — googletrans
            res = fallback_translator.translate(
                text, src=from_lang if from_lang != "auto" else "auto", dest=to_lang
            )
            return res.text
        except Exception as e:
            return f"⚠️ Tarjima xatosi: {str(e)}"


# --- Switch tillar funksiyasi ---
def switch_user_langs(user_id: int):
    sql.execute("SELECT from_lang, to_lang FROM user_languages WHERE user_id=%s", (user_id,))
    langs = sql.fetchone()
    if langs:
        from_lang, to_lang = langs
        sql.execute(
            "UPDATE user_languages SET from_lang=%s, to_lang=%s WHERE user_id=%s",
            (to_lang, from_lang, user_id)
        )
        db.commit()
        return True
    return False

# --- Helper: uzun matnlarni bo‘lib yuborish ---
async def split_and_send(msg: Message, text: str, reply_markup=None):
    limit = 4096
    parts = [text[i:i+limit] for i in range(0, len(text), limit)]
    for i, part in enumerate(parts):
        # Tugma faqat birinchi xabarda chiqadi
        if i == 0:
            await msg.answer(part, reply_markup=reply_markup)
        else:
            await msg.answer(part)

# --- Handlers ---
@translate_router.message(Command("lang"))
async def cmd_lang(msg: Message):
    await msg.answer(
        "🌤 Tillarni tanlang:\nChap: Kiruvchi | O‘ng: Chiquvchi\n"
        "🌤 Select languages:\nLeft: Input | Right: Output",
        reply_markup=get_language_keyboard(msg.from_user.id)
    )

@translate_router.message(Command("help"))
async def cmd_help(msg: Message):
    help_text = (
        "📚 <b>Tarjimon bot qo‘llanmasi</b>\n"
        "📚 <b>Translator bot guide</b>\n\n"
        "🔹 <b>/lang</b> — Kiruvchi va chiquvchi tillarni tanlash\n"
        "🔹 <b>/lang</b> — Select input and output languages\n"
        "🔹 Matn yuboring — Tanlangan tillarga tarjima qiladi\n"
        "🔹 Send text — Translates to selected languages\n"
        "🔹 Rasm captioni — Caption matnini tarjima qiladi\n"
        "🔹 Image caption — Translates the caption text\n"
        "🔹 Audio/Voice — Hozircha qo‘llab-quvvatlanmaydi\n"
        "🔹 Audio/Voice — Not supported yet\n\n"
        "🌐 Qo‘llab-quvvatlanadigan tillar:\n" +
        ", ".join([f"{v['flag']} {v['name']}" for v in LANGUAGES.values() if v['name'] != "Avto"])
    )
    await msg.answer(help_text, parse_mode="HTML")

@translate_router.callback_query(F.data.startswith("setlang:"))
async def cb_lang(callback: CallbackQuery):
    if callback.data == "setlang:ignore":
        await callback.answer("🛑 Mumkin emas / Not allowed")
    else:
        try:
            _, direction, lang_code = callback.data.split(":")
            update_user_lang(callback.from_user.id, lang_code, direction)
            await callback.message.edit_reply_markup(
                reply_markup=get_language_keyboard(callback.from_user.id)
            )
        except:
            pass
        try:
            await callback.answer("✅ Til yangilandi / Language updated")
        except:
            pass

@translate_router.callback_query(F.data.startswith("translate:"))
async def cb_translate_options(callback: CallbackQuery):
    action = callback.data.split(":")[1]
    if action == "setlang":
        kb = get_language_keyboard(callback.from_user.id)
        await callback.message.reply(
            "🌤 Tillarni tanlang:\nChap: Kiruvchi | O‘ng: Chiquvchi\n"
            "🌤 Select languages:\nLeft: Input | Right: Output",
            reply_markup=kb
        )
        await callback.answer()
    elif action == "switch":
        if switch_user_langs(callback.from_user.id):
            await callback.answer("✅ Tillar almashtirildi / Languages switched")
        else:
            await callback.answer("⚠️ Tillar topilmadi / Languages not found", show_alert=True)

@translate_router.message(F.text)
async def handle_text(msg: Message):
    check_status, channels = await CheckData.check_member(bot, msg.from_user.id)

    if not check_status:
        try:
            await msg.answer(
                "Kanallarimizga obuna bo'ling \n\nSubscribe to our channels",
                reply_markup=await UserPanels.join_btn(msg.from_user.id)
            )
        except:
            pass
        return  

    langs = get_user_langs(msg.from_user.id)
    if not langs:
        return await msg.answer("❗ Avval /lang orqali tillarni tanlang.\n❗ Please select languages via /lang.")
    from_lang, to_lang = langs
    if not to_lang:
        return await msg.answer("❗ Chiquvchi til tanlanmagan.\n❗ Output language not selected.")

    result = translate_text("auto" if from_lang == "auto" else from_lang, to_lang, msg.text)

    # Uzun matnni bo‘lib yuborish
    await split_and_send(msg, result, reply_markup=get_translation_keyboard())

@translate_router.message(F.voice | F.audio | F.video_note)
async def handle_audio(msg: Message):
    check_status, channels = await CheckData.check_member(bot, msg.from_user.id)

    if not check_status:
        try:
            await msg.answer(
                "Kanallarimizga obuna bo'ling \n\nSubscribe to our channels",
                reply_markup=await UserPanels.join_btn(msg.from_user.id)
            )
        except:
            pass
        return

    await msg.answer("🔊 Audio tarjimasi tez orada qo‘shiladi 😉\n🔊 Audio translation coming soon 😉")

@translate_router.message(F.caption)
async def handle_caption(msg: Message):
    check_status, channels = await CheckData.check_member(bot, msg.from_user.id)

    if not check_status:
        try:
            await msg.answer(
                "Kanallarimizga obuna bo'ling \n\nSubscribe to our channels",
                reply_markup=await UserPanels.join_btn(msg.from_user.id)
            )
        except:
            pass
        return

    langs = get_user_langs(msg.from_user.id)
    if not langs:
        return
    from_lang, to_lang = langs
    if not to_lang:
        return

    result = translate_text("auto" if from_lang == "auto" else from_lang, to_lang, msg.caption)

    # Uzun matnni bo‘lib yuborish
    await split_and_send(msg, result, reply_markup=get_translation_keyboard())