from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from src.handlers.users.translate import get_user_langs, LANGUAGES, translate_text
from uuid import uuid4

inline_router = Router()


@inline_router.inline_query()
async def inline_translate(query: InlineQuery):
    user_id = query.from_user.id
    text = query.query.strip()
    if not text:
        return

    # Foydalanuvchi sozlamalari
    langs = get_user_langs(user_id)
    if not langs:
        from_lang, to_lang = "auto", "uz"
    else:
        from_lang, to_lang = langs
        if not to_lang:
            to_lang = "uz"

    results = []

    # 1) Asosiy tarjima (foydalanuvchi to_lang)
    main_translation = translate_text("auto" if from_lang == "auto" else from_lang, to_lang, text)
    results.append(
        InlineQueryResultArticle(
            id=str(uuid4()),
            title=f"{LANGUAGES[to_lang]['flag']} {LANGUAGES[to_lang]['name']}",
            description=main_translation,
            input_message_content=InputTextMessageContent(
                message_text=f"<b>{main_translation}</b>\n\n<i>{text}</i>",
                parse_mode="HTML"
            )
        )
    )

    # 2) Qo‘shimcha tillar — dinamik shaklda, takrorlanmasin
    # Masalan, asosan ishlatiladigan tillar
    preferred_langs = ["en", "ru", "tr", "ar"]
    added_langs = {to_lang}  # allaqachon ishlatilgan tillar

    for lang in preferred_langs:
        if lang in added_langs:  # agar allaqachon ishlatilgan bo‘lsa — o‘tkazib yuboramiz
            continue
        try:
            translated = translate_text("auto", lang, text)
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"{LANGUAGES[lang]['flag']} {LANGUAGES[lang]['name']}",
                    description=translated,
                    input_message_content=InputTextMessageContent(
                        message_text=f"<b>{translated}</b>\n\n<i>{text}</i>",
                        parse_mode="HTML"
                    )
                )
            )
            added_langs.add(lang)
        except Exception:
            continue

    # 3) Agar `uz` yo‘q bo‘lsa — majburan qo‘shib qo‘yamiz
    if "uz" not in added_langs:
        try:
            uz_translation = translate_text("auto", "uz", text)
            results.append(
                InlineQueryResultArticle(
                    id=str(uuid4()),
                    title=f"{LANGUAGES['uz']['flag']} {LANGUAGES['uz']['name']}",
                    description=uz_translation,
                    input_message_content=InputTextMessageContent(
                        message_text=f"<b>{uz_translation}</b>\n\n<i>{text}</i>",
                        parse_mode="HTML"
                    )
                )
            )
        except Exception:
            pass

    await query.answer(results, cache_time=1, is_personal=True)
