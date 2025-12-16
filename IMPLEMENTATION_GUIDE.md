"""
🎯 BOTGA QANDAY YAXSHILANISHLAR KIRITILDI VA QANDAY ISHLATISH KERAK
=====================================================================

✅ 1. PROFESSIONAL LOGGING SYSTEM
==================================
📁 Fayl: src/utils/logger.py

🔹 Nima qiladi:
- Barcha loglarni logs/ papkasiga saqlaydi
- Har bir modul uchun alohida log fayli
- Error va warninglarni alohida fayl
- Log rotation (har bir fayl 10MB gacha)
- Console'da rangli output

🔹 Qanday ishlatish:

```python
from src.utils.logger import translate_logger, log_translation, log_user_action, log_error

# Oddiy log
translate_logger.info("Translation started")

# User action log
log_user_action(user_id, "translate", "uz -> en")

# Translation log
log_translation(user_id, "uz", "en", len(text))

# Error log
try:
    # kod
    pass
except Exception as e:
    log_error(e, "handle_text")
```

📊 Natija:
- logs/bot.log - barcha bot loglari
- logs/bot_errors.log - faqat errorlar
- logs/translate.log - tarjima loglari
- logs/users.log - user action loglari
- logs/database.log - database querylar


✅ 2. RATE LIMITING (SPAM PROTECTION)
======================================
📁 Fayl: src/utils/rate_limiter.py

🔹 Nima qiladi:
- 1 daqiqada 20ta so'rovdan ko'p bo'lsa bloklaydi
- 60 soniya ban
- Har bir user uchun alohida counting

🔹 Qanday ishlatish:

```python
from src.utils.rate_limiter import rate_limiter

# Handler boshida
allowed, message = rate_limiter.check_rate_limit(user_id)
if not allowed:
    return await msg.answer(message, parse_mode="HTML")

# Davom ettirish...
```

📊 Natija:
- Spam himoyasi
- Bot server resurslarini tejash
- DoS hujumlaridan himoya


✅ 3. TRANSLATION HISTORY
==========================
📁 Fayl: src/utils/translation_history.py

🔹 Nima qiladi:
- Har bir tarjimani database'ga saqlaydi
- Oxirgi 100ta tarjima saqlanadi
- Sevimli tarjimalar
- Statistika

🔹 Qanday ishlatish:

```python
from src.utils.translation_history import (
    save_translation_history,
    get_translation_history,
    get_user_translation_stats,
    toggle_favorite
)

# Tarjimani saqlash
save_translation_history(
    user_id=msg.from_user.id,
    from_lang="uz",
    to_lang="en",
    original_text="Salom",
    translated_text="Hello"
)

# Tarixni olish
history = get_translation_history(user_id, limit=10)
for id, from_lang, to_lang, original, translated, created_at in history:
    print(f"{original} -> {translated}")

# Statistika
stats = get_user_translation_stats(user_id)
print(f"Total: {stats['total']}, Today: {stats['today']}")

# Sevimliga qo'shish
toggle_favorite(user_id, translation_id)
```

📊 Natija:
- Foydalanuvchi o'z tarjimalarini ko'rishi mumkin
- Tez tarjima (tarixdan)
- Statistika


🎯 INTEGRATION QILISH
======================

1. translate.py ga qo'shish:
```python
# Import
from src.utils.logger import translate_logger, log_translation, log_error
from src.utils.rate_limiter import rate_limiter
from src.utils.translation_history import save_translation_history

# handle_text handlerda:
@translate_router.message(F.text)
async def handle_text(msg: Message):
    # Rate limiting
    allowed, message = rate_limiter.check_rate_limit(msg.from_user.id)
    if not allowed:
        return await msg.answer(message, parse_mode="HTML")
    
    # Logging
    translate_logger.info(f"User {msg.from_user.id} translating {len(msg.text)} chars")
    
    try:
        # Tarjima qilish
        result = translate_text(from_lang, to_lang, msg.text)
        
        # Tarixga saqlash
        save_translation_history(
            msg.from_user.id,
            from_lang,
            to_lang,
            msg.text,
            result
        )
        
        # Log
        log_translation(msg.from_user.id, from_lang, to_lang, len(msg.text))
        
        # Javob
        await msg.answer(result)
        
    except Exception as e:
        log_error(e, "handle_text")
        await msg.answer("Error...")
```

2. users.py ga qo'shish:
```python
from src.utils.logger import user_logger, log_user_action

@user_router.message(CommandStart())
async def start_cmd(message: Message):
    log_user_action(message.from_user.id, "start", "First interaction")
    # ...
```


🔧 QANDAY SOZLASH
==================

Rate Limiting o'zgartirish:
```python
# src/utils/rate_limiter.py da
self.MAX_REQUESTS_PER_MINUTE = 30  # 20 dan 30 ga
self.BAN_DURATION = 120  # 60 dan 120 ga
```

Log level o'zgartirish:
```python
# src/utils/logger.py da
logger.setLevel(logging.DEBUG)  # Barcha loglarni ko'rish uchun
logger.setLevel(logging.WARNING)  # Faqat warning va errorlar
```


📈 KELAJAKDA QO'SHISH KERAK
============================

1. /history command - tarjima tarixini ko'rish
2. /stats command - statistika
3. /favorites command - sevimli tarjimalar
4. Redis cache - tezlik uchun
5. Webhook o'rniga polling
6. Monitoring (Prometheus)
7. Database backup avtomatik
8. Multi-language UI


🎓 QANDAY TEST QILISH
======================

1. Logging test:
   - Botni ishga tushiring
   - Tarjima qiling
   - logs/ papkasini tekshiring
   - bot.log faylida loglar bo'lishi kerak

2. Rate limiting test:
   - Tez ketma-ket 25 ta xabar yuboring
   - 21-xabardan keyin "Too many requests" ko'rinishi kerak
   - 60 soniya kuting
   - Yana xabar yuborish mumkin bo'lishi kerak

3. History test:
   - Bir nechta tarjima qiling
   - Database'da translation_history jadvalini tekshiring
   - SELECT * FROM translation_history ORDER BY created_at DESC LIMIT 10;


💡 FOYDALI MASLAHATLAR
=======================

1. Log fayllarni muntazam tekshiring
2. Error loglarni har kuni ko'rib chiqing
3. Rate limit sozlamalarni load'ga qarab sozlang
4. Translation history'ni export qilish imkoniyatini qo'shing
5. Admin dashboard yarating


📞 QANDAY YORDAM OLISH
=======================

Agar muammo yuzaga kelsa:
1. logs/bot_errors.log ni tekshiring
2. Console outputni o'qing
3. Database connection'ni tekshiring
4. Import xatolarini tekshiring


✨ YAKUNIY NATIJA
==================

Bu yaxshilanishlar bot'ni:
- 🛡️ Xavfsizroq qiladi (spam himoyasi)
- 📊 Monitorlash oson (professional logging)
- 💾 Ma'lumotlar tarixini saqlaydi
- ⚡ Production-ready holatga yaqinlashtiradi
- 🎯 Professional standartlarga mos keltiradi

ESDA TUTING: Bu faqat boshlanish! Davom ettirib, yanada ko'p yaxshilanishlar kiritish mumkin! 🚀
"""
