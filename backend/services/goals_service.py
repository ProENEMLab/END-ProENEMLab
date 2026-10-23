from datetime import date, datetime, timezone

from services.exceptions import GoalsError
from models.engagement import DailyGoal
from repositories.goal_repository import GoalRepository
from services.points_service import PointsService
from services.streak_service import StreakService

class GoalsService:

    def __init__(
        self,
        goal_repository: GoalRepository,
        points_service: PointsService,
        streak_service: StreakService,
    ) -> None:
        self.goals = goal_repository
        self.points = points_service
        self.streak = streak_service

    def has_goal(self, user_id: int, day: date) -> bool:
        return bool(self.goals.list_for_date(user_id, day))

    def is_completed(self, user_id: int, day: date) -> bool:
        goals = self.goals.list_for_date(user_id, day)
        return bool(goals) and all(goal.is_completed for goal in goals)

    def list_goals(self, user_id: int, target_date: date | None = None) -> list[DailyGoal]:
        target_date = target_date or date.today()
        return self.goals.list_for_date(user_id, target_date)

    def get_today_goal(self, user_id: int, target_date: date | None = None) -> dict | None:
        target_date = target_date or date.today()
        goals = self.goals.list_for_date(user_id, target_date, prefer_open=True)
        if not goals:
            return None
        return goals[0].to_dict()

    def create_goal(self, user_id: int, description: str, target_date: date) -> DailyGoal:
        goal = DailyGoal(
            user_id=user_id,
            description=description.strip(),
            target_date=target_date,
            is_completed=False,
        )
        self.goals.add(goal)
        self.goals.commit()
        return goal

    def complete_goal(self, user_id: int, goal_id: int) -> DailyGoal:
        goal = self._require_owner(user_id, goal_id, "complete")
        if goal.is_completed:
            raise GoalsError("Goal already completed.", 400, "GOAL_ALREADY_COMPLETED")

        goal.is_completed = True
        goal.completed_at = datetime.now(timezone.utc)
        self.goals.flush()
        self.points.award_points(
            user_id,
            "goal_completed",
            reference_id=goal.id,
            commit=False,
        )
        self.streak.register_activity(user_id, commit=False)
        self.goals.commit()
        return goal

    def delete_goal(self, user_id: int, goal_id: int) -> None:
        goal = self._require_owner(user_id, goal_id, "delete")
        self.goals.delete(goal)
        self.goals.commit()

    def _require_owner(self, user_id: int, goal_id: int, action: str) -> DailyGoal:
        goal = self.goals.get_by_id(goal_id)
        if not goal:
            raise GoalsError("Goal not found.", 404, "GOAL_NOT_FOUND")
        if goal.user_id != user_id:
            raise GoalsError(
                f"You do not have permission to {action} this goal.",
                403,
                "FORBIDDEN",
            )
        return goal
