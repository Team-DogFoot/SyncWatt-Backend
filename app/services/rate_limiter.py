"""In-memory rate limiter. Single-instance/process only.
TODO: Replace with Redis for horizontal scaling."""
import logging
from collections import defaultdict
from datetime import date

logger = logging.getLogger(__name__)

DAILY_ANALYSIS_LIMIT = 3


class RateLimiter:
    def __init__(self, daily_limit: int = DAILY_ANALYSIS_LIMIT):
        self.daily_limit = daily_limit
        self._usage: dict[int, dict] = defaultdict(lambda: {"date": "", "count": 0})

    def check(self, chat_id: int) -> bool:
        """Return True if allowed, False if limit exceeded."""
        today = date.today().isoformat()
        usage = self._usage[chat_id]
        if usage["date"] != today:
            usage["date"] = today
            usage["count"] = 0
        return usage["count"] < self.daily_limit

    def increment(self, chat_id: int):
        """Increment usage count by 1."""
        today = date.today().isoformat()
        usage = self._usage[chat_id]
        if usage["date"] != today:
            usage["date"] = today
            usage["count"] = 0
        usage["count"] += 1
        remaining = self.daily_limit - usage["count"]
        logger.info(f"[RateLimit] chat_id={chat_id}: {usage['count']}/{self.daily_limit} (remaining: {remaining})")
