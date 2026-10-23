class DashboardService:

    def __init__(self, roadmap_service, goals_service, streak_service) -> None:
        self.roadmap = roadmap_service
        self.goals = goals_service
        self.streak = streak_service

    def get_dashboard(self, user_id: int) -> dict:
        next_step = self._next_step(self.roadmap.get_next_topic(user_id))
        daily_goal = self._daily_goal(self.goals.get_today_goal(user_id))
        streak = self.streak.get_current(user_id)
        return {
            "next_step": next_step,
            "daily_goal": daily_goal,
            "streak": {
                "current_streak": streak["current_streak"],
                "longest_streak": streak["longest_streak"],
            },
        }

    def _next_step(self, topic: dict | None) -> dict | None:
        if not topic:
            return None
        return {
            "topic_id": topic["id"],
            "topic_name": topic["name"],
            "subject": topic["subject"],
        }

    def _daily_goal(self, goal: dict | None) -> dict | None:
        if not goal:
            return None
        return {
            "id": goal["id"],
            "description": goal["description"],
            "is_completed": goal["is_completed"],
        }
