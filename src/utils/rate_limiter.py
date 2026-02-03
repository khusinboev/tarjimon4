"""
Rate limiting and spam protection
"""
from typing import Dict, Tuple
from time import time
from collections import defaultdict


class RateLimiter:
    """
    Rate limiter for spam protection
    """
    
    def __init__(self):
        # user_id -> (last_request_time, request_count, ban_until)
        self.users: Dict[int, Tuple[float, int, float]] = defaultdict(lambda: (0.0, 0, 0.0))
        
        # Sozlamalar
        self.MAX_REQUESTS_PER_MINUTE = 20
        self.BAN_DURATION = 60  # 1 daqiqa
        self.WINDOW = 60  # 1 daqiqa
        
    def check_rate_limit(self, user_id: int) -> Tuple[bool, str]:
        """
        Foydalanuvchi rate limitni tekshirish
        
        Returns:
            (allowed, message) - True agar ruxsat bo'lsa, False + xabar
        """
        current_time = time()
        last_time, count, ban_until = self.users[user_id]
        
        # Agar ban bo'lsa
        if ban_until > current_time:
            remaining = int(ban_until - current_time)
            return False, f"⏰ Siz {remaining} soniya davomida bloklangansiz. Iltimos, kuting."
        
        # Window restart
        if current_time - last_time > self.WINDOW:
            self.users[user_id] = (current_time, 1, 0.0)
            return True, ""
        
        # Request count yangilash
        new_count = count + 1
        self.users[user_id] = (last_time, new_count, ban_until)
        
        # Rate limit tekshirish
        if new_count > self.MAX_REQUESTS_PER_MINUTE:
            # Ban qilish
            ban_until = current_time + self.BAN_DURATION
            self.users[user_id] = (last_time, new_count, ban_until)
            return False, (
                "🚫 <b>Juda ko'p so'rov!</b>\n\n"
                f"Siz 1 daqiqada {self.MAX_REQUESTS_PER_MINUTE}ta so'rovdan ko'proq yubordingiz.\n"
                f"⏰ {self.BAN_DURATION} soniya davomida bloklangansiz.\n\n"
                "🚫 <b>Too many requests!</b>\n"
                f"You exceeded {self.MAX_REQUESTS_PER_MINUTE} requests per minute.\n"
                f"⏰ Blocked for {self.BAN_DURATION} seconds."
            )
        
        return True, ""
    
    def reset_user(self, user_id: int):
        """Foydalanuvchi rate limitni reset qilish"""
        if user_id in self.users:
            del self.users[user_id]
    
    def get_stats(self, user_id: int) -> str:
        """Foydalanuvchi rate limit statistikasini olish"""
        if user_id not in self.users:
            return "No data"
        
        last_time, count, ban_until = self.users[user_id]
        current_time = time()
        
        if ban_until > current_time:
            return f"Banned until {int(ban_until - current_time)}s"
        
        elapsed = current_time - last_time
        if elapsed > self.WINDOW:
            return "Clean slate"
        
        return f"{count}/{self.MAX_REQUESTS_PER_MINUTE} requests in last {int(elapsed)}s"


# Global rate limiter
rate_limiter = RateLimiter()
