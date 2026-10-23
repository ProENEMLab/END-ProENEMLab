from datetime import date, timedelta

from repositories.streak_repository import StreakRepository
from services.points_service import PointsService

MILESTONE_DAYS = 7

class StreakService:

    def __init__(
        self,
        streak_repository: StreakRepository,
        points_service: PointsService,
    ) -> None:
        self.streaks = streak_repository
        self.points = points_service

    def current_length(self, user_id: int) -> int:
        record = self.streaks.get_by_user(user_id)
        if not record:
            return 0
        return record.current_streak or 0

    def has_activity_on(self, user_id: int, day: date) -> bool:
        record = self.streaks.get_by_user(user_id)
        return bool(record and record.last_activity_date == day)

    def get_current(self, user_id: int) -> dict:
        record = self.streaks.get_by_user(user_id)
        if not record:
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_activity_date": None,
            }
        return record.to_dict()

    def register_activity(
        self,
        user_id: int,
        *,
        today: date | None = None,
        commit: bool = True,
    ) -> dict:
        today = today or date.today()
        record = self.streaks.get_or_create(user_id)
        if record.last_activity_date == today:
            if commit:
                self.streaks.commit()
            return record.to_dict()

        record.current_streak = self._next_streak(record, today)
        record.longest_streak = max(record.longest_streak or 0, record.current_streak)
        record.last_activity_date = today
        self._award_milestone(user_id, record.current_streak)
        if commit:
            self.streaks.commit()
        return record.to_dict()

    def _next_streak(self, record, today: date) -> int:
        yesterday = today - timedelta(days=1)
        if record.last_activity_date == yesterday:
            return (record.current_streak or 0) + 1
        return 1

    def _award_milestone(self, user_id: int, current_streak: int) -> None:
        if current_streak > 0 and current_streak % MILESTONE_DAYS == 0:
            self.points.award_points(
                user_id,
                "streak_bonus",
                reference_id=None,
                commit=False,
            )
