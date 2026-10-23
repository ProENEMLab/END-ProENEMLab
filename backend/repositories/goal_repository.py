from datetime import date

from models.engagement import DailyGoal
from repositories.base_repository import BaseRepository

class GoalRepository(BaseRepository):

    model = DailyGoal

    def list_for_date(
        self,
        user_id: int,
        target_date: date,
        *,
        prefer_open: bool = False,
    ) -> list[DailyGoal]:
        query = DailyGoal.query.filter_by(user_id=user_id, target_date=target_date)
        if prefer_open:
            query = query.order_by(DailyGoal.is_completed.asc(), DailyGoal.created_at.asc())
        else:
            query = query.order_by(DailyGoal.created_at.asc())
        return query.all()
