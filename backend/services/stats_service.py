from services.exceptions import StatsError
from models.attempt import ERROR_TYPES, Attempt
from repositories.attempt_repository import AttemptRepository

class StatsService:

    def __init__(self, attempt_repository: AttemptRepository) -> None:
        self.attempts = attempt_repository

    def get_performance(self, user_id: int) -> dict:
        total, correct = self.attempts.count_total_and_correct(user_id)
        by_topic = self._by_topic(user_id)
        return {
            "overall_accuracy": self._ratio(correct, total),
            "by_topic": by_topic,
            "by_subject": self._by_subject(user_id),
            "worst_topics": self._worst(by_topic),
            "error_breakdown": self._errors(user_id),
        }

    def set_error_type(self, user_id: int, attempt_id: int, error_type: str) -> Attempt:
        if error_type not in ERROR_TYPES:
            raise StatsError(
                "error_type must be 'conceito' or 'atencao'.",
                400,
                "INVALID_ERROR_TYPE",
            )
        attempt = self.attempts.get_by_id(attempt_id)
        if not attempt:
            raise StatsError("Attempt not found.", 404, "ATTEMPT_NOT_FOUND")
        if attempt.user_id != user_id:
            raise StatsError(
                "You do not have permission to update this attempt.",
                403,
                "FORBIDDEN",
            )
        if attempt.is_correct:
            raise StatsError(
                "Only incorrect attempts can be classified.",
                400,
                "ATTEMPT_IS_CORRECT",
            )
        attempt.error_type = error_type
        self.attempts.commit()
        return attempt

    def _ratio(self, correct: int, total: int) -> float:
        return round(correct / total, 4) if total else 0.0

    def _by_topic(self, user_id: int) -> list[dict]:
        rows = []
        for (
            topic_id,
            topic_name,
            total_attempts,
            correct_count,
        ) in self.attempts.performance_by_topic(user_id):
            total_attempts = int(total_attempts or 0)
            correct_count = int(correct_count or 0)
            rows.append(
                {
                    "topic_id": topic_id,
                    "topic_name": topic_name or f"Topic {topic_id}",
                    "accuracy": self._ratio(correct_count, total_attempts),
                    "total_attempts": total_attempts,
                }
            )
        rows.sort(key=lambda item: item["topic_id"])
        return rows

    def _worst(self, by_topic: list[dict]) -> list[dict]:
        ranked = [
            {
                "topic_id": topic["topic_id"],
                "topic_name": topic["topic_name"],
                "accuracy": topic["accuracy"],
            }
            for topic in by_topic
            if topic["total_attempts"] >= 1
        ]
        ranked.sort(key=lambda item: (item["accuracy"], item["topic_id"]))
        return ranked[:3]

    def _by_subject(self, user_id: int) -> list[dict]:
        rows = []
        for subject, total_attempts, correct_count in self.attempts.performance_by_subject(user_id):
            total_attempts = int(total_attempts or 0)
            correct_count = int(correct_count or 0)
            rows.append(
                {
                    "subject": subject,
                    "accuracy": self._ratio(correct_count, total_attempts),
                    "total_attempts": total_attempts,
                }
            )
        rows.sort(key=lambda item: item["accuracy"])
        return rows

    def _errors(self, user_id: int) -> dict:
        breakdown = {"conceito": 0, "atencao": 0, "nao_classificado": 0}
        for attempt in self.attempts.list_wrong(user_id):
            if attempt.error_type == "conceito":
                breakdown["conceito"] += 1
            elif attempt.error_type == "atencao":
                breakdown["atencao"] += 1
            else:
                breakdown["nao_classificado"] += 1
        return breakdown
