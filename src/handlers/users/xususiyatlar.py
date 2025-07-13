from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from deep_translator import GoogleTranslator

from config import sql, db

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

def translate_text(from_lang: str, to_lang: str, text: str) -> str:
    try:
        return GoogleTranslator(source=from_lang, target=to_lang).translate(text)
    except Exception as e:
        return f"⚠️ Tarjima xatosi: {e}"

def translate_auto(to_lang: str, text: str) -> str:
    return translate_text("auto", to_lang, text)
