"""
Professional logging system for Telegram bot
"""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

# Logs papkasini yaratish
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Custom formatter
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.INFO: blue + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - %(name)s - %(levelname)s - %(message)s" + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Professional logger setup with file and console handlers
    
    Args:
        name: Logger nomi
        level: Logging darajasi
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Agar logger allaqachon configured bo'lsa, qaytarish
    if logger.handlers:
        return logger
    
    # File handler - barcha loglar
    file_handler = RotatingFileHandler(
        logs_dir / f"{name}.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # File handler - faqat errorlar
    error_handler = RotatingFileHandler(
        logs_dir / f"{name}_errors.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColoredFormatter())
    
    # Handlerlarni qo'shish
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    
    return logger


# Global loggerlar
bot_logger = setup_logger('bot')
db_logger = setup_logger('database')
translate_logger = setup_logger('translate')
user_logger = setup_logger('users')
admin_logger = setup_logger('admin')


def log_user_action(user_id: int, action: str, details: str = ""):
    """Foydalanuvchi harakatlarini loglash"""
    user_logger.info(f"User {user_id} - {action} - {details}")


def log_translation(user_id: int, from_lang: str, to_lang: str, text_length: int):
    """Tarjimalarni loglash"""
    translate_logger.info(f"User {user_id} - {from_lang} -> {to_lang} - Length: {text_length}")


def log_error(error: Exception, context: str = ""):
    """Xatolarni loglash"""
    bot_logger.error(f"Error in {context}: {str(error)}", exc_info=True)


def log_db_query(query: str, execution_time: float):
    """Database querylarni loglash"""
    if execution_time > 1.0:  # Slow query warning
        db_logger.warning(f"Slow query ({execution_time:.2f}s): {query[:100]}...")
    else:
        db_logger.debug(f"Query ({execution_time:.3f}s): {query[:100]}...")
