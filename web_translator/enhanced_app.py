"""
🌐 Enhanced Web Translator Application
Modern Flask backend with advanced features
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, Tuple

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("web_translator")

# Initialize Flask app
app = Flask(__name__, 
            static_folder='static', 
            template_folder='templates',
            static_url_path='/static')

# Enable CORS
CORS(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Configuration
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "5000"))
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"

# Load languages
PROJECT_LANGUAGES = {
    "auto": {"name": "Avto-aniqlash", "flag": "🌐"},
    "uz": {"name": "O'zbek", "flag": "🇺🇿"},
    "en": {"name": "English", "flag": "🇬🇧"},
    "ru": {"name": "Русский", "flag": "🇷🇺"},
    "tr": {"name": "Türkçe", "flag": "🇹🇷"},
    "ar": {"name": "العربية", "flag": "🇸🇦"},
    "fr": {"name": "Français", "flag": "🇫🇷"},
    "de": {"name": "Deutsch", "flag": "🇩🇪"},
    "zh": {"name": "中文", "flag": "🇨🇳"},
    "ja": {"name": "日本語", "flag": "🇯🇵"},
    "ko": {"name": "한국어", "flag": "🇰🇷"},
    "hi": {"name": "हिन्दी", "flag": "🇮🇳"},
    "id": {"name": "Bahasa Indonesia", "flag": "🇮🇩"},
    "fa": {"name": "فارسی", "flag": "🇮🇷"},
    "es": {"name": "Español", "flag": "🇪🇸"},
    "it": {"name": "Italiano", "flag": "🇮🇹"},
    "kk": {"name": "Qazaqşa", "flag": "🇰🇿"},
    "ky": {"name": "Кыргызча", "flag": "🇰🇬"},
    "az": {"name": "Azərbaycan dili", "flag": "🇦🇿"},
    "tk": {"name": "Türkmençe", "flag": "🇹🇲"},
    "tg": {"name": "Тоҷикӣ", "flag": "🇹🇯"},
    "pl": {"name": "Polski", "flag": "🇵🇱"},
    "pt": {"name": "Português", "flag": "🇵🇹"},
    "am": {"name": "አማርኛ", "flag": "🇪🇹"},
    "uk": {"name": "Українська", "flag": "🇺🇦"},
    "cs": {"name": "Čeština", "flag": "🇨🇿"},
    "bg": {"name": "Български", "flag": "🇧🇬"},
    "ro": {"name": "Română", "flag": "🇷🇴"},
    "el": {"name": "Ελληνικά", "flag": "🇬🇷"},
}

# Translation cache (simple in-memory cache)
translation_cache: Dict[str, Dict[str, Any]] = {}


# ==========================================
# 🔧 HELPER FUNCTIONS
# ==========================================

def get_cache_key(text: str, src: str, dest: str) -> str:
    """Generate cache key for translation"""
    content = f"{text}:{src}:{dest}"
    return hashlib.md5(content.encode()).hexdigest()


def get_cached_translation(text: str, src: str, dest: str) -> Optional[str]:
    """Get cached translation if available"""
    if not CACHE_ENABLED:
        return None
    
    key = get_cache_key(text, src, dest)
    cached = translation_cache.get(key)
    
    if cached and cached.get('expires') > datetime.now():
        cached['hits'] = cached.get('hits', 0) + 1
        return cached.get('translated')
    
    return None


def set_cached_translation(text: str, src: str, dest: str, translated: str):
    """Cache translation result"""
    if not CACHE_ENABLED:
        return
    
    key = get_cache_key(text, src, dest)
    translation_cache[key] = {
        'translated': translated,
        'expires': datetime.now() + timedelta(days=7),
        'hits': 0,
        'created': datetime.now()
    }


def detect_language(text: str) -> str:
    """Simple language detection based on character patterns"""
    # Cyrillic detection
    if any('\u0400' <= char <= '\u04FF' for char in text):
        return 'ru'
    
    # Arabic detection
    if any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' for char in text):
        return 'ar'
    
    # CJK detection
    if any('\u4E00' <= char <= '\u9FFF' for char in text):
        return 'zh'
    
    # Japanese Hiragana/Katakana
    if any('\u3040' <= char <= '\u309F' or '\u30A0' <= char <= '\u30FF' for char in text):
        return 'ja'
    
    # Korean
    if any('\uAC00' <= char <= '\uD7AF' for char in text):
        return 'ko'
    
    # Default to English
    return 'en'


# ==========================================
# 🤖 TRANSLATION ENGINES
# ==========================================

def translate_with_deep_translator(text: str, src: str, dest: str) -> Tuple[str, Optional[str]]:
    """Translate using deep_translator library"""
    try:
        from deep_translator import GoogleTranslator
        
        if src == "auto":
            src = detect_language(text)
        
        translator = GoogleTranslator(source=src, target=dest)
        result = translator.translate(text)
        
        return result, src if src != "auto" else None
    except Exception as e:
        logger.error(f"Deep translator error: {e}")
        raise


def translate_with_googletrans(text: str, src: str, dest: str) -> Tuple[str, Optional[str]]:
    """Fallback translation using googletrans"""
    try:
        from googletrans import Translator
        
        translator = Translator()
        
        if src == "auto":
            result = translator.translate(text, dest=dest)
            return result.text, result.src
        else:
            result = translator.translate(text, src=src, dest=dest)
            return result.text, src
    except Exception as e:
        logger.error(f"Googletrans error: {e}")
        raise


def translate_with_libretranslate(text: str, src: str, dest: str) -> Tuple[str, Optional[str]]:
    """Alternative translation using LibreTranslate API"""
    try:
        import requests
        
        url = "https://libretranslate.de/translate"
        payload = {
            "q": text,
            "source": src if src != "auto" else "auto",
            "target": dest,
            "format": "text"
        }
        
        response = requests.post(url, data=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data.get("translatedText", ""), data.get("detectedLanguage", {}).get("language")
    except Exception as e:
        logger.error(f"LibreTranslate error: {e}")
        raise


def translate_text(text: str, src: str, dest: str) -> Dict[str, Any]:
    """
    Main translation function with fallback chain
    
    Priority:
    1. Check cache
    2. Try deep_translator (GoogleTranslator)
    3. Try googletrans as fallback
    4. Try LibreTranslate as last resort
    """
    import time
    start_time = time.time()
    
    # Check cache first
    cached = get_cached_translation(text, src, dest)
    if cached:
        logger.info(f"Cache hit for translation")
        return {
            "text": cached,
            "detected": None,
            "cached": True,
            "time_ms": int((time.time() - start_time) * 1000)
        }
    
    # Try translation engines in order
    engines = [
        ("deep_translator", translate_with_deep_translator),
        ("googletrans", translate_with_googletrans),
        ("libretranslate", translate_with_libretranslate),
    ]
    
    last_error = None
    
    for engine_name, engine_func in engines:
        try:
            logger.info(f"Trying translation with {engine_name}")
            translated, detected = engine_func(text, src, dest)
            
            # Cache successful translation
            set_cached_translation(text, src, dest, translated)
            
            return {
                "text": translated,
                "detected": detected,
                "engine": engine_name,
                "cached": False,
                "time_ms": int((time.time() - start_time) * 1000)
            }
        except Exception as e:
            logger.warning(f"{engine_name} failed: {e}")
            last_error = e
            continue
    
    # All engines failed
    raise RuntimeError(f"All translation engines failed. Last error: {last_error}")


# ==========================================
# 🛣️ ROUTES
# ==========================================

@app.route("/")
def index():
    """Main page with enhanced translator"""
    lang_map_json = json.dumps(PROJECT_LANGUAGES, ensure_ascii=False)
    return render_template("enhanced_index.html", 
                         languages=list(PROJECT_LANGUAGES.items()),
                         lang_map_json=lang_map_json,
                         max_len=MAX_TEXT_LENGTH)


@app.route("/api/languages")
def get_languages():
    """API endpoint to get available languages"""
    return jsonify({
        "success": True,
        "languages": PROJECT_LANGUAGES,
        "count": len(PROJECT_LANGUAGES)
    })


@app.route("/translate", methods=["POST"])
@limiter.limit("30 per minute")
def translate():
    """
    Translation API endpoint
    
    Request body:
    {
        "text": "Hello world",
        "source": "en" | "auto",
        "target": "uz"
    }
    
    Response:
    {
        "ok": true,
        "translated": "Salom dunyo",
        "detected": "en",
        "engine": "deep_translator",
        "time_ms": 123
    }
    """
    try:
        # Parse request
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        text = data.get("text", "").strip()
        src = data.get("source", data.get("src", "auto")).lower()
        dest = data.get("target", data.get("dest", data.get("target_lang", ""))).lower()
        
        # Validation
        if not text:
            return jsonify({
                "ok": False,
                "error": "Matn kiritilmagan",
                "error_code": "EMPTY_TEXT"
            }), 400
        
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({
                "ok": False,
                "error": f"Matn uzunligi {MAX_TEXT_LENGTH} belgidan oshmasligi kerak",
                "error_code": "TEXT_TOO_LONG"
            }), 400
        
        if not dest:
            return jsonify({
                "ok": False,
                "error": "Maqsad tili tanlanmagan",
                "error_code": "NO_TARGET_LANG"
            }), 400
        
        if dest not in PROJECT_LANGUAGES:
            return jsonify({
                "ok": False,
                "error": "Noto'g'ri maqsad tili",
                "error_code": "INVALID_TARGET_LANG"
            }), 400
        
        # Perform translation
        result = translate_text(text, src, dest)
        
        return jsonify({
            "ok": True,
            "translated": result["text"],
            "detected": result.get("detected"),
            "engine": result.get("engine"),
            "cached": result.get("cached", False),
            "time_ms": result.get("time_ms")
        })
        
    except Exception as e:
        logger.exception("Translation error")
        return jsonify({
            "ok": False,
            "error": str(e),
            "error_code": "TRANSLATION_ERROR"
        }), 500


@app.route("/api/detect", methods=["POST"])
def detect_language_api():
    """Language detection API"""
    try:
        data = request.get_json() or request.form
        text = data.get("text", "").strip()
        
        if not text:
            return jsonify({"ok": False, "error": "Matn kiritilmagan"}), 400
        
        detected = detect_language(text)
        
        return jsonify({
            "ok": True,
            "detected": detected,
            "language_name": PROJECT_LANGUAGES.get(detected, {}).get("name", detected),
            "flag": PROJECT_LANGUAGES.get(detected, {}).get("flag", "🏳️")
        })
    except Exception as e:
        logger.exception("Detection error")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/stats")
def get_stats():
    """Get translator statistics"""
    cache_size = len(translation_cache)
    cache_hits = sum(c.get('hits', 0) for c in translation_cache.values())
    
    return jsonify({
        "ok": True,
        "cache": {
            "size": cache_size,
            "total_hits": cache_hits
        },
        "supported_languages": len(PROJECT_LANGUAGES),
        "max_text_length": MAX_TEXT_LENGTH
    })


@app.route("/health")
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    })


# Static files
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "ok": False,
        "error": "Juda ko'p so'rov. Iltimos, biroz kuting.",
        "error_code": "RATE_LIMITED"
    }), 429


@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        "ok": False,
        "error": "Server xatosi yuz berdi",
        "error_code": "INTERNAL_ERROR"
    }), 500


# ==========================================
# 🚀 MAIN
# ==========================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    logger.info(f"Starting Enhanced Web Translator on port {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"Cache enabled: {CACHE_ENABLED}")
    logger.info(f"Max text length: {MAX_TEXT_LENGTH}")
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        threaded=True
    )
