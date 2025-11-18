from flask import Flask, render_template, request, jsonify
import importlib
import logging
import os
import json

app = Flask(__name__, static_folder='static', template_folder='templates')

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web_translator")

# Load languages from config.py (expecting LANGUAGES dict)
project_languages = None
try:
    import config as project_config
    project_languages = getattr(project_config, "LANGUAGES", None)
    if not isinstance(project_languages, dict):
        logger.warning("config.LANGUAGES exists but is not a dict; ignoring.")
        project_languages = None
    else:
        logger.info("Loaded LANGUAGES from config.py (%d entries)", len(project_languages))
except Exception as e:
    logger.info("config.py not found or error reading it: %s", e)
    project_languages = None

# Fallback default if config missing (shouldn't be used since you provided config.py)
if not project_languages:
    project_languages = {
        "auto": {"name": "Auto", "flag": "🌐"},
        "en": {"name": "English", "flag": "🇬🇧"},
        "ru": {"name": "Русский", "flag": "🇷🇺"},
        "uz": {"name": "Oʻzbek", "flag": "🇺🇿"},
    }

# Try to import translate function from main.py if available
translate_func = None
try:
    main_mod = importlib.import_module("main")
    translate_func = getattr(main_mod, "translate_text", None)
    if translate_func:
        logger.info("Using translate_text from main.py as primary translator")
except Exception as e:
    logger.info("main.py not importable or translate_text missing: %s", e)

# Fallback translator (googletrans)
translator = None
if not translate_func:
    try:
        from googletrans import Translator
        translator = Translator()
        logger.info("Using googletrans as fallback translator")
    except Exception as e:
        logger.warning("googletrans not available: %s", e)
        translator = None

MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))

def translate_with_fallback(text: str, src: str, dest: str):
    if not text:
        raise ValueError("Matn bo'sh")
    if len(text) > MAX_TEXT_LENGTH:
        raise ValueError(f"Matn uzunligi {MAX_TEXT_LENGTH} belgidan oshmasligi kerak")

    # Use repo's translate_text if available
    if translate_func:
        try:
            res = translate_func(text, src, dest)
            if isinstance(res, dict):
                return {"text": res.get("text") or res.get("translated_text") or "", "detected": res.get("src") or src}
            if hasattr(res, "text"):
                return {"text": getattr(res, "text", str(res)), "detected": getattr(res, "src", src)}
            return {"text": str(res), "detected": src}
        except TypeError:
            try:
                res = translate_func(text, dest)
                return {"text": str(res), "detected": src}
            except Exception as e:
                logger.exception("Error calling main.translate_text: %s", e)
        except Exception as e:
            logger.exception("Error in main.translate_text: %s", e)

    # googletrans fallback
    if translator:
        try:
            if src == "auto":
                result = translator.translate(text, dest=dest)
            else:
                result = translator.translate(text, src=src, dest=dest)
            return {"text": result.text, "detected": getattr(result, "src", src)}
        except Exception as e:
            logger.exception("googletrans error: %s", e)
            raise RuntimeError("Tarjima servisi bilan bog'liq muammo yuz berdi")

    raise RuntimeError("Hech qanday tarjima vositasi mavjud emas. Iltimos, server konfiguratsiyasini tekshiring.")

@app.route("/")
def index():
    # Prepare languages list for template in stable order (use insertion order of dict)
    languages_items = [(code, info.get("name"), info.get("flag")) for code, info in project_languages.items()]
    # Also pass the raw map as JSON for client-side lookup
    lang_map_json = json.dumps(project_languages, ensure_ascii=False)
    return render_template("index.html", languages=languages_items, lang_map_json=lang_map_json, max_len=MAX_TEXT_LENGTH)

@app.route("/translate", methods=["POST"])
def translate_route():
    data = request.get_json(silent=True) or request.form or {}
    text = data.get("text", "")
    src = data.get("source", "auto")
    dest = data.get("target") or data.get("target_lang") or ""
    if not dest:
        return jsonify({"ok": False, "error": "Maqsad tilini tanlang"}), 400
    try:
        text = str(text)
    except Exception:
        return jsonify({"ok": False, "error": "Matn noto'g'ri formatda"}), 400

    try:
        result = translate_with_fallback(text, src, dest)
        return jsonify({"ok": True, "translated": result["text"], "detected": result.get("detected", src)})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except RuntimeError as re:
        logger.error("Runtime error during translation: %s", re)
        return jsonify({"ok": False, "error": str(re)}), 502
    except Exception as e:
        logger.exception("Unexpected error during translation")
        return jsonify({"ok": False, "error": "Serverda kutilmagan xato yuz berdi"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)