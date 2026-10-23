from datetime import datetime, timedelta, timezone

from flask import current_app

from services.exceptions import ProgressionError
from models.learning import UserTopicLevel
from models.question import Question
from repositories.learning_repository import ProgressionRepository
from repositories.question_repository import QuestionRepository
from repositories.topic_repository import TopicRepository

LEVELS = ("easy", "medium", "hard")

class ProgressionService:

    def __init__(
        self,
        progression_repository: ProgressionRepository,
        question_repository: QuestionRepository,
        topic_repository: TopicRepository,
    ) -> None:
        self.progressions = progression_repository
        self.questions = question_repository
        self.topics = topic_repository

    def list_levels(self, user_id: int) -> list[dict]:
        return [row.to_dict() for row in self.progressions.list_for_user(user_id)]

    def get_status(self, user_id: int, topic_id: int) -> dict:
        topic = self._require_topic(topic_id)
        row = self._row(user_id, topic_id)
        levels = {
            level: self._level_block(user_id, topic_id, level, row.unlocked_level)
            for level in LEVELS
        }
        return {
            "topic_id": topic_id,
            "unlocked_level": row.unlocked_level,
            "levels": levels,
            "suggestion": self._suggestion(user_id, topic_id, row, topic.name),
        }

    def questions_for_level(self, user_id: int, topic_id: int, level: str) -> list[Question]:
        self._require_topic(topic_id)
        if level not in LEVELS:
            raise ProgressionError("level must be easy, medium or hard.", 400, "INVALID_LEVEL")
        row = self._row(user_id, topic_id)
        if LEVELS.index(level) > LEVELS.index(row.unlocked_level):
            raise ProgressionError("Este nível ainda está travado.", 403, "LEVEL_LOCKED")
        return self.questions.list_for_topic_level(topic_id, level)

    def summary(self, user_id: int) -> dict:
        since = datetime.now(timezone.utc) - timedelta(
            days=int(current_app.config["PROGRESSION_RECENT_DAYS"])
        )
        recent = []
        suggestions = []
        for row in self.progressions.list_for_user(user_id):
            topic = self.topics.get_by_id(row.topic_id)
            if not topic:
                continue
            status = self.get_status(user_id, row.topic_id)
            suggestion = dict(status["suggestion"])
            suggestion["topic_id"] = row.topic_id
            suggestion["topic_name"] = topic.name
            suggestions.append(suggestion)
            unlocked_at = _as_utc(row.unlocked_at)
            if row.unlocked_level != "easy" and unlocked_at and unlocked_at >= since:
                recent.append(
                    {
                        "topic_id": row.topic_id,
                        "topic_name": topic.name,
                        "unlocked_level": row.unlocked_level,
                        "unlocked_at": unlocked_at.isoformat(),
                    }
                )
        return {"recent_unlocks": recent, "suggestions": suggestions}

    def practice_question(self, user_id: int, topic_id: int) -> Question | None:
        self._require_topic(topic_id)
        row = self._row(user_id, topic_id)
        index = LEVELS.index(row.unlocked_level)
        return self.progressions.next_question(user_id, topic_id, list(LEVELS[: index + 1]))

    def on_attempt(self, user_id: int, question_id: int) -> dict | None:
        question = self.questions.get_by_id(question_id)
        if not question or not question.topic_id or question.difficulty not in LEVELS:
            return None
        row = self._row(user_id, question.topic_id)
        if question.difficulty != row.unlocked_level:
            return None
        index = LEVELS.index(row.unlocked_level)
        if index >= len(LEVELS) - 1:
            return None
        if not self._can_advance(user_id, question.topic_id, row.unlocked_level):
            return None
        row.unlocked_level = LEVELS[index + 1]
        row.unlocked_at = datetime.now(timezone.utc)
        self.progressions.commit()
        topic = self.topics.get_by_id(question.topic_id)
        return {
            "type": "advance",
            "topic_id": question.topic_id,
            "level": row.unlocked_level,
            "message": self._text(
                "advance",
                level_name=self._name(row.unlocked_level),
                topic_name=topic.name if topic else "",
            ),
        }

    def _can_advance(self, user_id: int, topic_id: int, level: str) -> bool:
        total, correct, needed = self._target(user_id, topic_id, level)
        if needed <= 0 or total < needed:
            return False
        percent = int(current_app.config["PROGRESSION_UNLOCK_PERCENT"])
        return correct * 100 >= percent * total

    def _target(self, user_id: int, topic_id: int, level: str) -> tuple[int, int, int]:
        attempts = self._first_attempts(user_id, topic_id, level)
        window = attempts[-int(current_app.config["PROGRESSION_WINDOW"]) :]
        available = self.questions.count_with_difficulty(topic_id, level)
        minimum = int(current_app.config["PROGRESSION_MIN_ATTEMPTS"])
        needed = available if available < minimum else minimum
        total = len(window)
        correct = sum(1 for attempt in window if attempt.is_correct)
        return total, correct, needed

    def _first_attempts(self, user_id: int, topic_id: int, level: str):
        rows = self.progressions.attempts_for_level(user_id, topic_id, level)
        first = {}
        for row in rows:
            first.setdefault(row.question_id, row)
        return list(first.values())

    def _level_block(self, user_id: int, topic_id: int, level: str, unlocked: str) -> dict:
        if LEVELS.index(level) > LEVELS.index(unlocked):
            return {"status": "locked"}
        total, correct, needed = self._target(user_id, topic_id, level)
        available = self.questions.count_with_difficulty(topic_id, level)
        minimum = int(current_app.config["PROGRESSION_MIN_ATTEMPTS"])
        few = available < minimum
        payload = {
            "status": "unlocked",
            "accuracy": round(correct / total, 4) if total else 0,
            "attempts_in_window": total,
        }
        if few:
            payload["reason"] = "few_questions"
        if level == unlocked and LEVELS.index(level) < len(LEVELS) - 1:
            nxt = {
                "needed_accuracy": int(current_app.config["PROGRESSION_UNLOCK_PERCENT"]) / 100,
                "needed_attempts": needed,
            }
            if few:
                nxt["reason"] = "few_questions"
            payload["to_unlock_next"] = nxt
        return payload

    def _suggestion(
        self, user_id: int, topic_id: int, row: UserTopicLevel, topic_name: str
    ) -> dict:
        facts = self._suggestion_facts(user_id, topic_id, row, topic_name)
        if facts["just"]:
            return self._advance_suggestion(facts)
        few = self._few_questions_suggestion(facts)
        if few:
            return few
        reinforce = self._reinforce_suggestion(facts)
        if reinforce:
            return reinforce
        if facts["nxt"] is None:
            return self._max_level_suggestion(facts)
        short = self._accuracy_suggestion(facts)
        if short:
            return short
        return self._remaining_suggestion(facts)

    def _suggestion_facts(self, user_id, topic_id, row, topic_name):
        level = row.unlocked_level
        total, correct, needed = self._target(user_id, topic_id, level)
        available = self.questions.count_with_difficulty(topic_id, level)
        minimum = int(current_app.config["PROGRESSION_MIN_ATTEMPTS"])
        index = LEVELS.index(level)
        return {
            "level": level,
            "topic_name": topic_name,
            "total": total,
            "correct": correct,
            "needed": needed,
            "available": available,
            "few": available < minimum,
            "previous": self._neighbor(index, -1),
            "nxt": self._neighbor(index, 1),
            "percent": self._percent(correct, total),
            "reinforce": int(current_app.config["PROGRESSION_REINFORCE_PERCENT"]),
            "just": self._just_unlocked(level, total, _as_utc(row.unlocked_at)),
            "passed": self._passed_gate(needed, total, correct),
        }

    def _neighbor(self, index, step):
        other = index + step
        if other < 0 or other >= len(LEVELS):
            return None
        return LEVELS[other]

    def _percent(self, correct, total):
        if not total:
            return 0
        return int(round((correct * 100) / total))

    def _just_unlocked(self, level, total, unlocked_at):
        if level == "easy" or total or unlocked_at is None:
            return False
        elapsed = (datetime.now(timezone.utc) - unlocked_at).total_seconds()
        limit = int(current_app.config["PROGRESSION_JUST_UNLOCKED_SECONDS"])
        return elapsed <= limit

    def _passed_gate(self, needed, total, correct):
        if needed <= 0 or total < needed:
            return False
        needed_percent = int(current_app.config["PROGRESSION_UNLOCK_PERCENT"])
        return correct * 100 >= needed_percent * total

    def _advance_suggestion(self, facts):
        return self._suggestion_payload(
            "advance",
            facts["level"],
            self._text(
                "advance",
                level_name=self._name(facts["level"]),
                topic_name=facts["topic_name"],
            ),
        )

    def _few_questions_suggestion(self, facts):
        if not facts["nxt"] or not facts["few"] or facts["passed"]:
            return None
        return self._suggestion_payload(
            "not_enough_questions",
            facts["level"],
            self._text(
                "not_enough_questions",
                available=facts["available"],
                level_name=self._name(facts["level"]),
                needed_percent=int(current_app.config["PROGRESSION_UNLOCK_PERCENT"]),
                next_name=self._name(facts["nxt"]),
            ),
            reason="few_questions",
        )

    def _reinforce_suggestion(self, facts):
        if not facts["previous"] or not facts["total"]:
            return None
        if facts["correct"] * 100 >= facts["reinforce"] * facts["total"]:
            return None
        return self._suggestion_payload(
            "reinforce",
            facts["level"],
            self._text(
                "reinforce",
                level_name=self._name(facts["level"]),
                reinforce_percent=facts["reinforce"],
                previous_name=self._name(facts["previous"]),
            ),
        )

    def _max_level_suggestion(self, facts):
        return self._suggestion_payload(
            "keep_practicing",
            facts["level"],
            self._text(
                "max_level",
                level_name=self._name(facts["level"]),
                topic_name=facts["topic_name"],
            ),
        )

    def _accuracy_suggestion(self, facts):
        unlock = int(current_app.config["PROGRESSION_UNLOCK_PERCENT"])
        if facts["total"] < facts["needed"]:
            return None
        if facts["correct"] * 100 >= unlock * facts["total"]:
            return None
        return self._suggestion_payload(
            "keep_practicing",
            facts["level"],
            self._text(
                "keep_practicing_accuracy",
                attempts=facts["total"],
                level_name=self._name(facts["level"]),
                percent=facts["percent"],
                needed_percent=unlock,
            ),
        )

    def _remaining_suggestion(self, facts):
        remaining = max(facts["needed"] - facts["total"], 0)
        return self._suggestion_payload(
            "keep_practicing",
            facts["level"],
            self._text(
                "keep_practicing",
                remaining=remaining,
                level_name=self._name(facts["level"]),
                next_name=self._name(facts["nxt"]),
            ),
        )

    def _suggestion_payload(self, kind: str, level: str, message: str, reason: str | None = None):
        payload = {"type": kind, "level": level, "message": message}
        if reason:
            payload["reason"] = reason
        return payload

    def _text(self, key: str, **values) -> str:
        return current_app.config["PROGRESSION_MESSAGES"][key].format(**values)

    def _name(self, level: str) -> str:
        return current_app.config["PROGRESSION_LEVEL_NAMES"][level]

    def _row(self, user_id: int, topic_id: int) -> UserTopicLevel:
        row = self.progressions.get_for(user_id, topic_id)
        if row:
            return row
        row = UserTopicLevel(
            user_id=user_id,
            topic_id=topic_id,
            unlocked_level="easy",
            unlocked_at=datetime.now(timezone.utc),
        )
        self.progressions.add(row)
        self.progressions.commit()
        return row

    def _require_topic(self, topic_id: int):
        topic = self.topics.get_by_id(topic_id)
        if not topic:
            raise ProgressionError("Topic not found.", 404, "TOPIC_NOT_FOUND")
        return topic

def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
