import asyncio
import random
from io import BytesIO
from aiogram import Router, F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from deep_translator import GoogleTranslator
from googletrans import Translator as GoogleTransFallback

from config import sql, db, bot, ADMIN_ID, LANGUAGES
from src.keyboards.buttons import UserPanels
from src.keyboards.keyboard_func import CheckData

# Optional imports - graceful fallback if modules not available
try:
    from src.utils.logger import translate_logger, log_translation, log_error, log_user_action
    LOGGING_ENABLED = True
except ImportError:
    LOGGING_ENABLED = False
    class FakeLogger:
        def debug(self, msg): print(f"[DEBUG] {msg}")
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARNING] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    translate_logger = FakeLogger()
    log_translation = lambda *args, **kwargs: None
    log_error = lambda *args, **kwargs: None
    log_user_action = lambda *args, **kwargs: None

try:
    from src.utils.rate_limiter import rate_limiter
    RATE_LIMITING_ENABLED = True
except ImportError:
    RATE_LIMITING_ENABLED = False
    class FakeRateLimiter:
        def check_rate_limit(self, user_id):
            return True, ""
    rate_limiter = FakeRateLimiter()

try:
    from src.utils.translation_history import save_translation_history, get_translation_history, get_user_translation_stats
    HISTORY_ENABLED = True
except ImportError:
    HISTORY_ENABLED = False
    save_translation_history = lambda *args, **kwargs: None
    get_translation_history = lambda *args, **kwargs: []
    get_user_translation_stats = lambda user_id: {
        'total': 0, 'today': 0, 'this_month': 0, 
        'favorites': 0, 'most_used_lang_pair': None
    }

try:
    from src.utils.gamification import (
        award_translation_xp, 
        check_user_achievements,
        DailyChallengeManager,
        GamificationEngine
    )
    GAMIFICATION_ENABLED = True
except ImportError:
    GAMIFICATION_ENABLED = False
    award_translation_xp = lambda *args, **kwargs: {}
    check_user_achievements = lambda *args, **kwargs: []
    DailyChallengeManager = None
    GamificationEngine = None

translate_router = Router()

# Fallback translator instance
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
    buttons = []
    # Header row
    buttons.append([
        InlineKeyboardButton(
            text=f"{'✅ ' if from_lang == 'auto' else ''}🌐 Avto",
            callback_data="setlang:from:auto"
        ),
        InlineKeyboardButton(text=" ", callback_data="setlang:ignore"),
        InlineKeyboardButton(
            text=f"{'✅ ' if to_lang == 'auto' else ''}🌐 Avto",
            callback_data="setlang:to:auto"
        )
    ])
    # Language rows
    for code, data in LANGUAGES.items():
        if code == "auto": continue
        buttons.append([
            InlineKeyboardButton(
                text=f"{'✅ ' if from_lang == code else ''}{data['flag']} {data['name']}",
                callback_data=f"setlang:from:{code}"
            ),
            InlineKeyboardButton(text=" ", callback_data="setlang:ignore"),
            InlineKeyboardButton(
                text=f"{'✅ ' if to_lang == code else ''}{data['flag']} {data['name']}",
                callback_data=f"setlang:to:{code}"
            )
        ])
    # Back button
    buttons.append([
        InlineKeyboardButton(text="⬅️ Orqaga / Back", callback_data="setlang:back")
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
        result = GoogleTranslator(source=from_lang, target=to_lang).translate(text)
        return result if result else f"⚠️ Tarjima xatosi: Bo'sh natija"
    except Exception:
        try:
            # Fallback — googletrans
            res = fallback_translator.translate(
                text, src=from_lang if from_lang != "auto" else "auto", dest=to_lang
            )
            return res.text if res and res.text else f"⚠️ Tarjima xatosi: Bo'sh natija"
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
        "🌐 <b>Tillarni tanlang</b>\n"
        "✅ Chap: Kiruvchi (Input) | ✅ O‘ng: Chiquvchi (Output)\n"
        "<i>Til ustiga bosing va tanlang. Orqaga qaytish uchun ⬅️ tugmasini bosing.</i>",
        reply_markup=get_language_keyboard(msg.from_user.id),
        parse_mode="HTML"
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
    elif callback.data == "setlang:back":
        await callback.message.delete()
        await callback.answer()
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
            "🌐 <b>Tillarni tanlang</b>\n"
            "✅ Chap: Kiruvchi (Input) | ✅ O‘ng: Chiquvchi (Output)\n"
            "<i>Til ustiga bosing va tanlang. Orqaga qaytish uchun ⬅️ tugmasini bosing.</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await callback.answer()
    elif action == "switch":
        if switch_user_langs(callback.from_user.id):
            await callback.answer("✅ Tillar almashtirildi / Languages switched")
        else:
            await callback.answer("⚠️ Tillar topilmadi / Languages not found", show_alert=True)

MAIN_MENU_BUTTONS = {
    "🌐 Tilni tanlash",
    "📝 Tarjima qilish",
    "📅 Dars jadvali",
    "ℹ️ Yordam",
    "📚 Lug'atlar va Mashqlar",
}

@translate_router.message(F.text)
async def handle_text(msg: Message):
    # Ignore main menu button texts so they are not translated
    if msg.text in MAIN_MENU_BUTTONS:
        translate_logger.debug(f"Skipped main menu button text: {msg.text}")
        raise SkipHandler()
    
    # Rate limiting - spam protection
    allowed, rate_message = rate_limiter.check_rate_limit(msg.from_user.id)
    if not allowed:
        translate_logger.warning(f"Rate limit exceeded for user {msg.from_user.id}")
        return await msg.answer(rate_message, parse_mode="HTML")
    
    # Log user action
    log_user_action(msg.from_user.id, "translate_text", f"Text length: {len(msg.text)}")
    
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

    try:
        langs = get_user_langs(msg.from_user.id)
        if not langs:
            return await msg.answer(
                "🌐 <b>Tillarni tanlamadingiz</b>\n\n"
                "Tarjima qilish uchun avval tillarni tanlang:\n"
                "➡️ Bosh menyudagi '🌐 Tilni tanlash' tugmasini bosing\n\n"
                "🌐 <b>Languages not selected</b>\n\n"
                "To translate, first select languages:\n"
                "➡️ Press '🌐 Tilni tanlash' in main menu",
                parse_mode="HTML"
            )
        from_lang, to_lang = langs
        if not to_lang:
            return await msg.answer(
                "❗ <b>Chiquvchi til tanlanmagan</b>\n\n"
                "'🌐 Tilni tanlash' orqali chiquvchi tilni tanlang (o'ng ustun)\n\n"
                "❗ <b>Output language not selected</b>\n\n"
                "Select output language via '🌐 Tilni tanlash' (right column)",
                parse_mode="HTML"
            )

        # Tarjima qilish
        result = translate_text("auto" if from_lang == "auto" else from_lang, to_lang, msg.text)
        
        # Agar tarjima xatosi bo'lsa (xatolik yo'ki empty result)
        if not result or result.startswith("⚠️ Tarjima xatosi:"):
            log_error(Exception(result or "Empty translation result"), "translate_text")
            empty_result_msg = "⚠️ Tarjima xatosi: Bo'sh natija"
            await msg.answer(
                f"{result or empty_result_msg}\n\n"
                "🔄 Iltimos, qaytadan urinib ko'ring yoki tillarni tekshiring.\n"
                "🔄 Please try again or check your language settings.",
                reply_markup=get_translation_keyboard()
            )
        else:
            # Tarjimani tarixga saqlash
            try:
                save_translation_history(
                    user_id=msg.from_user.id,
                    from_lang=from_lang,
                    to_lang=to_lang,
                    original_text=msg.text[:500],  # 500 ta belgigacha saqlash
                    translated_text=result[:500]
                )
                log_translation(msg.from_user.id, from_lang, to_lang, len(msg.text))
                translate_logger.info(f"Translation saved for user {msg.from_user.id}: {from_lang}->{to_lang}")
            except Exception as e:
                log_error(e, "save_translation_history")
                translate_logger.error(f"Failed to save translation history: {e}")
            
            # Uzun matnni bo'lib yuborish
            await split_and_send(msg, result, reply_markup=get_translation_keyboard())
            
            # Award XP for translation
            if GAMIFICATION_ENABLED:
                try:
                    xp_result = award_translation_xp(msg.from_user.id, len(msg.text))
                    if xp_result and xp_result.get("level_up"):
                        await msg.answer(
                            f"🎉 <b>Level up!</b>\n"
                            f"Siz {xp_result.get('new_level', '?')}-levelga ko'tarildingiz!\n"
                            f"💎 Jami XP: {xp_result.get('total_xp', 0)}",
                            parse_mode="HTML"
                        )
                    
                    # Update daily challenge progress
                    if DailyChallengeManager:
                        try:
                            DailyChallengeManager.update_progress(msg.from_user.id, "translations", 1)
                        except Exception as e:
                            translate_logger.debug(f"Daily challenge update failed: {e}")
                    
                    # Check for new achievements
                    new_achievements = check_user_achievements(msg.from_user.id)
                    if new_achievements:
                        for ach in new_achievements:
                            if ach and isinstance(ach, dict):
                                await msg.answer(
                                    f"🏆 <b>Yangi yutuq!</b>\n"
                                    f"{ach.get('code', 'Achievement')} ochildi!\n"
                                    f"🎁 +{ach.get('xp_reward', 0)} XP",
                                    parse_mode="HTML"
                                )
                except Exception as e:
                    translate_logger.error(f"Gamification error: {e}")
    except Exception as e:
        log_error(e, "handle_text")
        translate_logger.error(f"Translation error for user {msg.from_user.id}: {e}")
        await msg.answer(
            "❌ <b>Tarjima xatosi</b>\n\n"
            "Tarjima qilishda xatolik yuz berdi. Iltimos, qaytadan urinib ko'ring.\n\n"
            "❌ <b>Translation error</b>\n\n"
            "An error occurred during translation. Please try again.",
            parse_mode="HTML"
        )

@translate_router.message(F.voice | F.audio | F.video_note)
async def handle_audio(msg: Message):
    try:
        check_status, channels = await CheckData.check_member(bot, msg.from_user.id)
    except Exception as e:
        translate_logger.error(f"Failed to check member status: {e}")
        check_status = True

    if not check_status:
        try:
            await msg.answer(
                "📌 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
                "📌 Subscribe to our channels to use the bot:",
                reply_markup=await UserPanels.join_btn(msg.from_user.id)
            )
        except Exception as e:
            translate_logger.error(f"Failed to send subscription message: {e}")
        return

    await msg.answer(
        "🔊 <b>Audio tarjima</b>\n\n"
        "Audio va ovozli xabarlar tarjimasi tez orada qo'shiladi!\n"
        "🕒 Hozircha faqat matnli tarjima mavjud.\n\n"
        "🔊 <b>Audio translation</b>\n\n"
        "Audio and voice message translation coming soon!\n"
        "🕒 Currently only text translation is available.",
        parse_mode="HTML"
    )

@translate_router.message(F.photo | F.document | F.video)
async def handle_media(msg: Message):
    """Rasm, document va video uchun handler."""
    try:
        check_status, channels = await CheckData.check_member(bot, msg.from_user.id)
    except Exception as e:
        translate_logger.error(f"Failed to check member status: {e}")
        check_status = True

    if not check_status:
        try:
            await msg.answer(
                "📌 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
                "📌 Subscribe to our channels to use the bot:",
                reply_markup=await UserPanels.join_btn(msg.from_user.id)
            )
        except Exception as e:
            translate_logger.error(f"Failed to send subscription message: {e}")
        return

    # Agar caption bo'lsa, uni tarjima qilamiz
    if msg.caption:
        try:
            langs = get_user_langs(msg.from_user.id)
            if not langs:
                return await msg.answer(
                    "🌐 Avval tillarni tanlang: '🌐 Tilni tanlash'\n"
                    "🌐 Select languages first: '🌐 Tilni tanlash'"
                )
            from_lang, to_lang = langs
            if not to_lang:
                return await msg.answer(
                    "❗ Chiquvchi tilni tanlang\n"
                    "❗ Select output language"
                )

            result = translate_text("auto" if from_lang == "auto" else from_lang, to_lang, msg.caption)
            
            # Agar tarjima xatosi bo'lsa (xatolik yo'ki empty result)
            if not result or result.startswith("⚠️ Tarjima xatosi:"):
                await msg.answer(f"{result or '⚠️ Xatolik'}\n\n🔄 Qaytadan urinib ko'ring / Try again")
            else:
                await msg.answer(
                    f"📝 <b>Caption tarjimasi:</b>\n\n{result}",
                    reply_markup=get_translation_keyboard(),
                    parse_mode="HTML"
                )
                
                # Award XP for caption translation (smaller amount)
                if GAMIFICATION_ENABLED:
                    try:
                        xp_result = award_translation_xp(msg.from_user.id, len(msg.caption))
                        if xp_result and xp_result.get("level_up"):
                            await msg.answer(
                                f"🎉 <b>Level up!</b>\n"
                                f"Siz {xp_result.get('new_level', '?')}-levelga ko'tarildingiz!",
                                parse_mode="HTML"
                            )
                        
                        # Update daily challenge progress
                        if DailyChallengeManager:
                            try:
                                DailyChallengeManager.update_progress(msg.from_user.id, "translations", 1)
                            except Exception as e:
                                translate_logger.debug(f"Daily challenge update failed: {e}")
                        
                        # Check for new achievements
                        new_achievements = check_user_achievements(msg.from_user.id)
                        if new_achievements:
                            for ach in new_achievements:
                                if ach and isinstance(ach, dict):
                                    await msg.answer(
                                        f"🏆 <b>Yangi yutuq!</b> {ach.get('code', 'Achievement')} ochildi! 🎁 +{ach.get('xp_reward', 0)} XP",
                                        parse_mode="HTML"
                                    )
                    except Exception as e:
                        translate_logger.error(f"Gamification error: {e}")
        except Exception as e:
            translate_logger.error(f"Media caption translation error: {e}")
            await msg.answer(
                "❌ Caption tarjima xatosi. Qaytadan urinib ko'ring.\n"
                "❌ Caption translation error. Please try again."
            )
    else:
        # Caption bo'lmasa, faylni qabul qilganimizni bildirish
        media_type = "🖼 Rasm" if msg.photo else ("📄 Hujjat" if msg.document else "🎥 Video")
        await msg.answer(
            f"{media_type} qabul qilindi!\n\n"
            "📝 Agar caption tarjima qilmoqchi bo'lsangiz, media bilan birga caption yuboring.\n\n"
            f"{media_type} received!\n\n"
            "📝 To translate a caption, send media with caption text.",
            parse_mode="HTML"
        )


# ==================== TARJIMA TARIXI ====================

@translate_router.message(Command("history"))
async def show_translation_history(msg: Message):
    """Oxirgi 10ta tarjimani ko'rsatish"""
    if not HISTORY_ENABLED:
        return await msg.answer(
            "⚠️ <b>Feature mavjud emas</b>\n\n"
            "Tarjima tarixi funksiyasi hozircha faol emas.\n\n"
            "⚠️ <b>Feature not available</b>\n\n"
            "Translation history feature is currently unavailable.",
            parse_mode="HTML"
        )
    
    try:
        log_user_action(msg.from_user.id, "view_history", "Requested translation history")
        
        history = get_translation_history(msg.from_user.id, limit=10)
        
        if not history:
            await msg.answer(
                "📭 <b>Tarjima tarixi bo'sh</b>\n\n"
                "Hali hech qanday tarjima qilmadingiz.\n\n"
                "📭 <b>Translation history is empty</b>\n\n"
                "You haven't made any translations yet.",
                parse_mode="HTML"
            )
            return
        
        text = "📚 <b>Oxirgi 10ta tarjima:</b>\n\n"
        
        for idx, (id, from_lang, to_lang, original, translated, created_at) in enumerate(history, 1):
            # Matnni qisqartirish
            short_original = original[:30] + "..." if len(original) > 30 else original
            short_translated = translated[:30] + "..." if len(translated) > 30 else translated
            
            # Sanani formatlash
            date_str = created_at.strftime("%d.%m.%Y %H:%M")
            
            text += (
                f"{idx}. 🔤 <code>{from_lang}</code> → <code>{to_lang}</code>\n"
                f"   📝 {short_original}\n"
                f"   ➡️ {short_translated}\n"
                f"   🕐 {date_str}\n\n"
            )
        
        text += (
            "💡 <i>Ko'proq ma'lumot olish uchun /stats buyrug'ini kiriting.</i>\n\n"
            "💡 <i>Use /stats command for more information.</i>"
        )
        
        await msg.answer(text, parse_mode="HTML")
        translate_logger.info(f"History shown to user {msg.from_user.id}")
        
    except Exception as e:
        log_error(e, "show_translation_history")
        await msg.answer(
            "❌ <b>Xatolik</b>\n\n"
            "Tarjima tarixini yuklashda xatolik yuz berdi.\n\n"
            "❌ <b>Error</b>\n\n"
            "Failed to load translation history.",
            parse_mode="HTML"
        )


@translate_router.message(Command("stats"))
async def show_user_stats(msg: Message):
    """Foydalanuvchi statistikasini ko'rsatish"""
    if not HISTORY_ENABLED:
        return await msg.answer(
            "⚠️ <b>Feature mavjud emas</b>\n\n"
            "Statistika funksiyasi hozircha faol emas.\n\n"
            "⚠️ <b>Feature not available</b>\n\n"
            "Statistics feature is currently unavailable.",
            parse_mode="HTML"
        )
    
    try:
        log_user_action(msg.from_user.id, "view_stats", "Requested statistics")
        
        stats = get_user_translation_stats(msg.from_user.id)
        
        no_data_uz = "Ma'lumot yo'q"
        no_data_en = "No data"
        
        text = (
            "📊 <b>Sizning statistikangiz:</b>\n\n"
            f"🔢 Jami tarjimalar: <b>{stats['total']}</b>\n"
            f"📅 Bugungi tarjimalar: <b>{stats['today']}</b>\n"
            f"📆 Oylik tarjimalar: <b>{stats['this_month']}</b>\n"
            f"⭐ Sevimli tarjimalar: <b>{stats['favorites']}</b>\n\n"
            f"🎯 Eng ko'p ishlatiladigan til: <b>{stats['most_used_lang_pair'] or no_data_uz}</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📊 <b>Your Statistics:</b>\n\n"
            f"🔢 Total translations: <b>{stats['total']}</b>\n"
            f"📅 Today's translations: <b>{stats['today']}</b>\n"
            f"📆 This month: <b>{stats['this_month']}</b>\n"
            f"⭐ Favorite translations: <b>{stats['favorites']}</b>\n\n"
            f"🎯 Most used language pair: <b>{stats['most_used_lang_pair'] or no_data_en}</b>\n\n"
            "💡 <i>/history - oxirgi tarjimalarni ko'rish</i>\n"
            "💡 <i>/history - view recent translations</i>"
        )
        
        await msg.answer(text, parse_mode="HTML")
        translate_logger.info(f"Stats shown to user {msg.from_user.id}")
        
    except Exception as e:
        log_error(e, "show_user_stats")
        await msg.answer(
            "❌ <b>Xatolik</b>\n\n"
            "Statistikani yuklashda xatolik yuz berdi.\n\n"
            "❌ <b>Error</b>\n\n"
            "Failed to load statistics.",
            parse_mode="HTML"
        )
