import asyncio
from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from config import LANGUAGES
from src.handlers.users.translate import get_user_langs, translate_text
from uuid import uuid4

inline_router = Router()


# Tarjimani fon thread’da ishlatish uchun
async def safe_translate(from_lang: str, to_lang: str, text: str):
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: translate_text(from_lang, to_lang, text))
    except Exception:
        return None


@inline_router.inline_query()
async def inline_translate(query: InlineQuery):
    user_id = query.from_user.id
    text = query.query.strip()

    # ❌ Agar foydalanuvchi hech narsa yozmagan bo‘lsa
    if not text:
        await query.answer(
            [
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title="ℹ️ Matn kiriting",
                    description="🇺🇿 yoki 🇬🇧 tillarida tarjima uchun matn yozing",
                    input_message_content=InputTextMessageContent(
                        message_text="✍️ Tarjima qilish uchun matn kiriting."
                    ),
                )
            ],
            cache_time=10,
            is_personal=True
        )
        return

    # ✅ Foydalanuvchi sozlamalari
    langs = get_user_langs(user_id)
    if not langs:
        from_lang, to_lang = "auto", "uz"
    else:
        from_lang, to_lang = langs
        if not to_lang:
            to_lang = "uz"

    results = []
    added_langs = set()

    # 1) Asosiy tarjima (foydalanuvchi to_lang)
    main_translation = await safe_translate("auto" if from_lang == "auto" else from_lang, to_lang, text)
    if main_translation:
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{LANGUAGES[to_lang]['flag']} {LANGUAGES[to_lang]['name']}",
                description=main_translation,
                input_message_content=InputTextMessageContent(
                    message_text=f"<i>{text}</i>\n\n<b>{main_translation}</b>",
                    parse_mode="HTML"
                )
            )
        )
        added_langs.add(to_lang)

    # 2) Qo‘shimcha tillar (takrorlanmasin)
    preferred_langs = ["en", "ru", "tr", "ar"]
    tasks = []
    for lang in preferred_langs:
        if lang in added_langs:
            continue
        tasks.append((lang, safe_translate("auto", lang, text)))

    # 3) Agar `uz` yo‘q bo‘lsa → majburan qo‘shamiz
    if "uz" not in added_langs and "uz" not in [l for l, _ in tasks]:
        tasks.append(("uz", safe_translate("auto", "uz", text)))

    # Parallel bajarish
    translations = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

    for (lang, _), translated in zip(tasks, translations):
        if not translated or isinstance(translated, Exception):
            continue
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{LANGUAGES[lang]['flag']} {LANGUAGES[lang]['name']}",
                description=translated,
                input_message_content=InputTextMessageContent(
                    message_text=f"<i>{text}</i>\n\n<b>{translated}</b>",
                    parse_mode="HTML"
                )
            )
        )
        added_langs.add(lang)

    # Javob qaytarish
    await query.answer(results, cache_time=30, is_personal=True)
