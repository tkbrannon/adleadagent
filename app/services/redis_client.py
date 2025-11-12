"""Redis client for caching and state management"""
import redis
from typing import Optional
from datetime import datetime, timedelta
from app.config import get_settings
from loguru import logger

settings = get_settings()


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self.client = redis.from_url(settings.redis_url, decode_responses=True)
    
    def mark_email_processed(self, email_id: str) -> bool:
        """Mark an email as processed to prevent duplicates"""
        key = f"processed_email:{email_id}"
        # Store for 7 days
        return self.client.setex(key, timedelta(days=7), "1")
    
    def is_email_processed(self, email_id: str) -> bool:
        """Check if email has been processed"""
        key = f"processed_email:{email_id}"
        return self.client.exists(key) > 0
    
    def store_lead_timestamp(self, phone: str, timestamp: datetime) -> None:
        """Store when lead email was received"""
        key = f"lead_timestamp:{phone}"
        self.client.setex(key, timedelta(hours=24), timestamp.isoformat())
    
    def get_lead_timestamp(self, phone: str) -> Optional[datetime]:
        """Get when lead email was received"""
        key = f"lead_timestamp:{phone}"
        ts = self.client.get(key)
        if ts:
            return datetime.fromisoformat(ts)
        return None
    
    def store_call_data(self, call_sid: str, data: dict) -> None:
        """Store call data temporarily"""
        key = f"call_data:{call_sid}"
        # Store each field separately for easy access
        for field, value in data.items():
            self.client.hset(key, field, str(value))
        self.client.expire(key, timedelta(hours=24))
    
    def get_call_data(self, call_sid: str) -> Optional[dict]:
        """Get call data"""
        key = f"call_data:{call_sid}"
        data = self.client.hgetall(key)
        return data if data else None
    
    def update_call_answer(self, call_sid: str, question_id: str, answer: str) -> None:
        """Store answer to a specific question"""
        key = f"call_data:{call_sid}"
        self.client.hset(key, f"answer_{question_id}", answer)
    
    def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Singleton instance
redis_client = RedisClient()
