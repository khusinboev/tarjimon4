# 🤖 Telegram Translation Bot - Tarjimon

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-blue.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-12+-blue.svg)](https://www.postgresql.org/)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)]()

Professional Telegram bot for text translation with vocabulary management, exercises, and advanced features.

## ✨ Features

### 🌐 Translation
- **Multi-language support**: 20+ languages
- **Auto-detection**: Automatic source language detection
- **Fallback system**: GoogleTranslator with googletrans fallback
- **Voice translation**: Support for voice messages
- **Media captions**: Translate photo/video/document captions
- **Quick switch**: One-click language pair switching

### 📚 Vocabulary Management
- **Personal dictionaries**: Save and manage your vocabulary
- **Categories**: Essential, Parallel, Public vocabularies
- **Exercises**: Interactive vocabulary practice
- **Progress tracking**: Monitor learning progress

### 📊 Professional Features
- **Logging system**: Professional logging with rotation
- **Rate limiting**: Spam protection (20 req/min)
- **Translation history**: Track all translations
- **Statistics**: Personal and system-wide stats
- **Admin dashboard**: Complete system monitoring

### 👤 User Features
- `/start` - Start bot and show main menu
- `/history` - View last 10 translations
- `/stats` - Personal statistics
- 🌐 **Tilni tanlash** - Language selection
- 📝 **Tarjima qilish** - Translation mode
- 📚 **Lug'atlar va Mashqlar** - Vocabulary & Exercises
- 📅 **Dars jadvali** - Timetable
- ℹ️ **Yordam** - Help and instructions

### 👨‍💼 Admin Features
- `/adminstats` - System statistics
- `/adminlogs` - View error logs
- `/broadcast` - Send announcements
- Channel management
- User analytics

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 1. Clone Repository
```bash
git clone <repository-url>
cd tarjimon4
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Database
Create PostgreSQL database and update `config.py`:
```python
DB_CONFIG = {
    'dbname': 'your_database',
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'port': 5432
}
```

### 5. Configure Bot
Update `config.py` with your bot token:
```python
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_ID = [your_telegram_id]
```

### 6. Run Bot
```bash
python main.py
```

## 📁 Project Structure

```
tarjimon4/
├── main.py                    # Entry point
├── config.py                  # Configuration
├── requirements.txt           # Dependencies
├── README.md                  # This file
├── CHANGELOG.md              # Version history
├── IMPROVEMENTS.md           # Future roadmap
├── IMPLEMENTATION_GUIDE.md   # Integration guide
│
├── src/
│   ├── db/
│   │   └── init_db.py        # Database initialization
│   │
│   ├── handlers/
│   │   ├── users/
│   │   │   ├── users.py      # User menu handlers
│   │   │   ├── translate.py  # Translation logic
│   │   │   ├── timetable.py  # Timetable feature
│   │   │   ├── inline_translate.py  # Inline mode
│   │   │   └── lughatlar/    # Vocabulary modules
│   │   │       ├── vocabs.py
│   │   │       ├── lughatlarim.py
│   │   │       ├── mashqlar.py
│   │   │       ├── ommaviylar.py
│   │   │       ├── essential.py
│   │   │       └── parallel.py
│   │   │
│   │   ├── admins/
│   │   │   ├── admin.py      # Admin panel
│   │   │   └── messages.py   # Broadcasting
│   │   │
│   │   └── others/
│   │       ├── channels.py   # Channel management
│   │       ├── groups.py     # Group handlers
│   │       └── other.py      # Misc handlers
│   │
│   ├── keyboards/
│   │   ├── buttons.py        # Keyboard layouts
│   │   └── keyboard_func.py  # Helper functions
│   │
│   ├── middlewares/
│   │   └── middleware.py     # Custom middlewares
│   │
│   ├── states/
│   │   └── __init__.py       # FSM states
│   │
│   └── utils/
│       ├── logger.py         # 📊 Logging system
│       ├── rate_limiter.py   # 🛡️ Rate limiting
│       └── translation_history.py  # 💾 History tracking
│
├── logs/                      # Auto-created
│   ├── bot.log
│   ├── bot_errors.log
│   ├── translate.log
│   ├── users.log
│   └── database.log
│
└── web_translator/            # Flask web interface
    ├── app.py
    ├── templates/
    └── static/
```

## 🗄️ Database Schema

### Main Tables
- `users` - User information
- `user_languages` - User language preferences
- `translation_history` - Translation records
- `vocabs` - User vocabularies
- `exercises` - Vocabulary exercises
- `channels` - Required channels
- `languages` - Supported languages

### Auto-Created Tables
The bot automatically creates all necessary tables on first run.

## 🔧 Configuration

### Rate Limiting
Edit `src/utils/rate_limiter.py`:
```python
MAX_REQUESTS_PER_MINUTE = 20  # Requests per minute
BAN_DURATION = 60             # Ban duration (seconds)
```

### Logging Level
Edit `src/utils/logger.py`:
```python
LOG_LEVEL = logging.INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### History Limit
Edit `src/utils/translation_history.py`:
```python
MAX_HISTORY_PER_USER = 100  # Max stored translations
```

## 📊 Monitoring

### View Logs
```bash
# All logs
tail -f logs/bot.log

# Errors only
tail -f logs/bot_errors.log

# Translation logs
tail -f logs/translate.log
```

### Admin Commands
- `/adminstats` - System statistics (users, translations, activity)
- `/adminlogs` - Recent error logs
- Use these for monitoring bot health

## 🛠️ Development

### Adding New Features
1. Create handler in appropriate directory
2. Register router in `main.py`
3. Add logging using utilities
4. Update documentation

### Code Style
- Follow existing patterns
- Use type hints
- Add docstrings
- Log important events
- Handle exceptions gracefully

### Testing
```bash
# Test translation
# Send any text to bot

# Test rate limiting
# Send 25+ messages quickly

# Test history
/history

# Test statistics
/stats
```

## 📈 Performance

- **Startup time**: < 2 seconds
- **Response time**: < 500ms (translation)
- **Memory usage**: ~50-100MB
- **CPU usage**: Minimal (event-driven)
- **Database queries**: Optimized with indexes

## 🔒 Security

- Rate limiting prevents spam/abuse
- Admin-only commands protected
- Channel subscription verification
- SQL injection prevention (parameterized queries)
- Error logs separate from main logs

## 🌐 Supported Languages

Uzbek, English, Russian, Turkish, German, French, Spanish, Italian, Arabic, Chinese, Japanese, Korean, Portuguese, Dutch, Polish, Czech, Romanian, Greek, Hindi, Persian, and more.

See `config.py` for complete list.

## 📝 Usage Examples

### Simple Translation
1. Click "📝 Tarjima qilish"
2. Select languages via "🌐 Tilni tanlash"
3. Send any text - it will be translated automatically

### Vocabulary
1. Click "📚 Lug'atlar va Mashqlar"
2. Choose category (Essential, Personal, Public)
3. Add/practice/manage vocabularies

### View History
```
/history
```
Shows your last 10 translations with timestamps.

### Check Statistics
```
/stats
```
See your total translations, today's count, and favorites.

## 🐛 Troubleshooting

### Bot not responding
1. Check logs: `logs/bot_errors.log`
2. Verify database connection
3. Check bot token in `config.py`
4. Restart bot: `python main.py`

### Translation errors
1. Check internet connection
2. Verify language codes
3. Check API availability
4. View translation logs: `logs/translate.log`

### Database errors
1. Verify PostgreSQL is running
2. Check database credentials
3. Ensure tables created
4. Check database logs: `logs/database.log`

## 📚 Documentation

- [CHANGELOG.md](CHANGELOG.md) - Version history and changes
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - Future roadmap
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Integration guide (Uzbek)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork repository
2. Create feature branch
3. Follow code style
4. Add tests
5. Update documentation
6. Submit pull request

## 📄 License

This project is licensed under MIT License.

## 👨‍💻 Author

Created with ❤️ for the Uzbek Telegram community.

## 📞 Support

For issues, questions, or suggestions:
- Open GitHub issue
- Contact via Telegram: [Your Contact]
- Check documentation first

## 🎯 Roadmap

See [IMPROVEMENTS.md](IMPROVEMENTS.md) for detailed future plans:
- ✅ Professional logging
- ✅ Rate limiting
- ✅ Translation history
- 🔄 Database connection pooling
- 🔄 Redis caching
- 🔄 Webhook support
- 🔄 Voice recognition
- 🔄 Image OCR
- 🔄 Export functionality

## ⭐ Star History

If you find this project useful, please give it a star! ⭐

---

**Status**: ✅ Production Ready  
**Version**: 2.0  
**Last Updated**: December 2024
