```markdown
# Oddiy Web Tarjimon (takomillashtirilgan UI)

Bu loyiha Flask orqali ishlaydigan web-tarjimon namunasi. U quyidagilarni ta'minlaydi:
- Config (repo ichidagi `config.py`) da berilgan tillarni ishlatish.
- Agar repoda `main.py` ichida `translate_text` funksiyasi bo'lsa — uni ishlatish.
- Aks holda `googletrans` bilan fallback.
- Chiroyli, responsiv UI (Bootstrap), nusxalash, tozalash, tilni almashtirish, va xatoliklar bilan ishlash.

O'rnatish:
1. Virtual environment yaratish va uni yoqish.
2. `pip install -r requirements.txt`
3. `python app.py` yoki `FLASK_APP=app.py flask run`
4. Brauzerda: http://localhost:5000

Muhim:
- Agar `main.py` yoki `config.py` dan maxsus API kalitlari/sörovlar talab qilinsa, `.env` fayliga yoki mos joyga qo'shing va `main.py` import qilishdan oldin kerakli env o'zgaruvchilarni berkitilgan holda qo'ying.
- Server yonida maksimal matn uzunligi `MAX_TEXT_LENGTH` muhit (ENV) orqali  sozlanadi (default 5000 belgi).

Fayllar:
- app.py — Flask backend, xatoliklarni qaytaradi
- templates/index.html — chiroyli UI
- static/style.css — qo'shimcha uslublar
- static/app.js — interaktivlik va so'rovlar