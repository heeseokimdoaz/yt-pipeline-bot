from datetime import date

from app.config import settings


class QuotaTracker:
    """Simple in-memory YouTube API quota tracker. Resets daily."""

    def __init__(self, daily_limit: int | None = None):
        self.daily_limit = daily_limit or settings.youtube_daily_quota_limit
        self.used = 0
        self.current_date = date.today()

    def _reset_if_new_day(self):
        if date.today() != self.current_date:
            self.used = 0
            self.current_date = date.today()

    def consume(self, units: int) -> bool:
        self._reset_if_new_day()
        if self.used + units > self.daily_limit:
            return False
        self.used += units
        return True

    @property
    def remaining(self) -> int:
        self._reset_if_new_day()
        return max(0, self.daily_limit - self.used)


quota_tracker = QuotaTracker()
