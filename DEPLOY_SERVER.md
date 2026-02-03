# 🚀 SERVER'GA DEPLOY QILISH YO'RIQNOMASI

## 📋 Kerakli fayllar

Yangi qo'shilgan fayllarni serverga yuklashingiz kerak:

### 1. Utility modullar (MAJBURIY)
```bash
src/utils/logger.py
src/utils/rate_limiter.py
src/utils/translation_history.py
```

### 2. Yangilangan fayllar
```bash
src/handlers/users/translate.py      # Yangilangan
src/handlers/admins/admin.py         # Yangilangan (/adminstats, /adminlogs)
```

### 3. Documentation (opsional)
```bash
README.md
CHANGELOG.md
IMPLEMENTATION_GUIDE.md
DEPLOY_SERVER.md  # Bu fayl
```

---

## 🔧 DEPLOY QILISH TARTIBI

### Variant 1: SCP orqali yuklash (tavsiya etiladi)

#### Windows dan:
```bash
# Utility fayllarni yuklash
scp src/utils/logger.py root@your-server:/home/tarjimon4/tarjimon4/src/utils/
scp src/utils/rate_limiter.py root@your-server:/home/tarjimon4/tarjimon4/src/utils/
scp src/utils/translation_history.py root@your-server:/home/tarjimon4/tarjimon4/src/utils/

# Yangilangan fayllarni yuklash
scp src/handlers/users/translate.py root@your-server:/home/tarjimon4/tarjimon4/src/handlers/users/
scp src/handlers/admins/admin.py root@your-server:/home/tarjimon4/tarjimon4/src/handlers/admins/
```

#### Linux/Mac dan:
```bash
# Barcha kerakli fayllarni yuklash
rsync -avz --progress \
  src/utils/*.py \
  root@your-server:/home/tarjimon4/tarjimon4/src/utils/

rsync -avz --progress \
  src/handlers/users/translate.py \
  src/handlers/admins/admin.py \
  root@your-server:/home/tarjimon4/tarjimon4/src/handlers/
```

---

### Variant 2: Git orqali yuklash

```bash
# Local da
git add .
git commit -m "Added professional features: logging, rate limiting, history"
git push origin main

# Server da
cd /home/tarjimon4/tarjimon4
git pull origin main
```

---

### Variant 3: FTP/SFTP orqali yuklash

FileZilla, WinSCP yoki boshqa FTP client orqali quyidagi fayllarni yuklang:
- `src/utils/` papkasidagi barcha fayllar
- `src/handlers/users/translate.py`
- `src/handlers/admins/admin.py`

---

## ✅ DEPLOY TEKSHIRISH

Server'da:

### 1. Fayllar mavjudligini tekshirish
```bash
cd /home/tarjimon4/tarjimon4

# Utility modullarni tekshirish
ls -la src/utils/
# Ko'rinishi kerak:
# logger.py
# rate_limiter.py
# translation_history.py
```

### 2. Syntax xatolarini tekshirish
```bash
python -m py_compile src/utils/logger.py
python -m py_compile src/utils/rate_limiter.py
python -m py_compile src/utils/translation_history.py
python -m py_compile src/handlers/users/translate.py
```

Agar xato bo'lmasa, hech narsa chiqmaydi.

### 3. Import xatolarini tekshirish
```bash
python -c "from src.utils.logger import translate_logger; print('✅ Logger OK')"
python -c "from src.utils.rate_limiter import rate_limiter; print('✅ Rate Limiter OK')"
python -c "from src.utils.translation_history import save_translation_history; print('✅ History OK')"
```

### 4. Bot ishga tushurish
```bash
# Test rejimida
python main.py

# Agar xato bo'lmasa, background'da ishga tushurish
nohup python main.py > bot.log 2>&1 &

# Yoki screen bilan
screen -S tarjimon_bot
python main.py
# Ctrl+A, D - detach qilish
```

---

## 🔍 XATOLIKLARNI ANIQLASH

### Xato: ModuleNotFoundError: No module named 'src.utils.logger'

**Sabab:** Fayl serverga yuklanmagan

**Yechim:**
```bash
# Fayl mavjudligini tekshiring
ls -la src/utils/logger.py

# Agar yo'q bo'lsa, yuklang
scp src/utils/logger.py root@your-server:/home/tarjimon4/tarjimon4/src/utils/
```

### Xato: SyntaxError

**Sabab:** Fayl noto'g'ri yuklangan yoki buzilgan

**Yechim:**
```bash
# Faylni qayta yuklang
scp -r src/utils/*.py root@your-server:/home/tarjimon4/tarjimon4/src/utils/
```

### Xato: PermissionError

**Sabab:** Faylga yozish huquqi yo'q

**Yechim:**
```bash
# Huquqlarni to'g'rilash
chmod +x main.py
chmod -R 755 src/
```

---

## 📊 YANGI FEATURELAR ISHLASHINI TEKSHIRISH

Bot ishga tushgandan keyin:

### 1. Logging tekshirish
```bash
# Loglar yaratilganmi?
ls -la logs/
# Ko'rinishi kerak:
# bot.log
# bot_errors.log
# translate.log
# users.log

# Log yozilayaptimi?
tail -f logs/bot.log
```

### 2. Rate limiting tekshirish
```bash
# Telegram'dan botga 25 ta xabar tez-tez yuboring
# 21-xabardan keyin "Too many requests" xabari chiqishi kerak
```

### 3. Translation history tekshirish
```bash
# Botga tarjima uchun matn yuboring
# Keyin /history commandini yuboring
# Tarjima tarixi ko'rinishi kerak
```

### 4. Statistics tekshirish
```bash
# Botga /stats commandini yuboring
# Statistika ko'rinishi kerak
```

### 5. Admin commands tekshirish (faqat adminlar)
```bash
# Botga /adminstats commandini yuboring
# Sistema statistikasi ko'rinishi kerak

# /adminlogs commandini yuboring
# Error loglar ko'rinishi kerak
```

---

## ⚙️ VAQTINCHA YECHIM (Agar fayllarni yuklashning imkoni bo'lmasa)

Yangi featurelar **optional** qilingan - agar utility modullar topilmasa, bot odatdagidek ishlaydi:

✅ Bot ishga tushadi  
✅ Translation ishlaydi  
⚠️ Logging faqat print orqali  
⚠️ Rate limiting faol emas  
⚠️ History/stats mavjud emas (xabar ko'rsatadi)  

Fayllarni keyinroq yuklasangiz ham bo'ladi - bot restart qilganingizda yangi featurelar avtomatik faollashadi.

---

## 📦 TO'LIQ BACKUP OLISH

Deploydan oldin backup oling:

```bash
# Server da
cd /home/tarjimon4
tar -czf tarjimon4_backup_$(date +%Y%m%d).tar.gz tarjimon4/

# Yoki rsync bilan
rsync -avz --progress \
  root@your-server:/home/tarjimon4/tarjimon4/ \
  ./backup_tarjimon4/
```

---

## 🔄 ROLLBACK (Orqaga qaytish)

Agar muammo yuzaga kelsa:

```bash
# Backup'dan qaytarish
cd /home/tarjimon4
rm -rf tarjimon4/
tar -xzf tarjimon4_backup_YYYYMMDD.tar.gz

# Bot'ni qayta ishga tushurish
cd tarjimon4
python main.py
```

---

## 📞 YORDAM

Agar muammo hal bo'lmasa:

1. **Loglarni tekshiring:**
   ```bash
   tail -100 logs/bot_errors.log
   ```

2. **Python versiyasini tekshiring:**
   ```bash
   python --version
   # 3.8+ bo'lishi kerak
   ```

3. **Dependencies tekshiring:**
   ```bash
   pip list | grep aiogram
   pip list | grep psycopg2
   ```

4. **Database'ni tekshiring:**
   ```bash
   psql -U your_user -d your_db -c "\dt"
   ```

---

## ✨ DEPLOY MUVAFFAQIYATLI BO'LGANIDAN KEYIN

1. ✅ Bot ishga tushdi
2. ✅ Xatolar yo'q
3. ✅ Loglar yozilmoqda
4. ✅ Rate limiting ishlayapti
5. ✅ History saqlanmoqda
6. ✅ Admin dashboard ishlayapti

**Tabriklayman! Bot production-ready holatda!** 🎉

---

## 📈 MONITORING

Bot ishlab turganda monitoring:

```bash
# Loglarni real-time kuzatish
tail -f logs/bot.log

# Error loglar
tail -f logs/bot_errors.log

# Translation loglar
tail -f logs/translate.log

# CPU/Memory usage
top -p $(pgrep -f "python main.py")

# Disk usage
df -h
du -sh logs/
```

---

**Eslatma:** Agar deploy jarayonida muammo yuzaga kelsa, BACKUP'ingiz borligiga ishonch hosil qiling!
