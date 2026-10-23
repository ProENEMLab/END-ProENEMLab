from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload

from models.attempt import Attempt
from models.learning import ReviewCycle, ReviewEvent, UserTopicLevel
from models.question import Question
from repositories.base_repository import BaseRepository

class ProgressionRepository(BaseRepository):

    model = UserTopicLevel

    def get_for(self, user_id: int, topic_id: int) -> UserTopicLevel | None:
        return UserTopicLevel.query.filter_by(user_id=user_id, topic_id=topic_id).first()

    def list_for_user(self, user_id: int) -> list[UserTopicLevel]:
        return (
            UserTopicLevel.query.filter_by(user_id=user_id).order_by(UserTopicLevel.topic_id).all()
        )

    def attempts_for_level(self, user_id: int, topic_id: int, level: str) -> list[Attempt]:
        return (
            Attempt.query.join(Question, Attempt.question_id == Question.id)
            .filter(
                Attempt.user_id == user_id,
                Question.topic_id == topic_id,
                Question.difficulty == level,
            )
            .order_by(Attempt.answered_at.asc(), Attempt.id.asc())
            .all()
        )

    def next_question(self, user_id: int, topic_id: int, levels: list[str]) -> Question | None:
        answered = (
            Attempt.query.filter_by(user_id=user_id).with_entities(Attempt.question_id).distinct()
        )
        return (
            Question.query.filter(
                Question.topic_id == topic_id,
                or_(Question.difficulty.in_(levels), Question.difficulty.is_(None)),
                Question.id.notin_(answered),
            )
            .order_by(Question.enem_index.asc(), Question.id.asc())
            .first()
        )

class ReviewRepository(BaseRepository):

    model = ReviewCycle

    def _with_question(self):
        return ReviewCycle.query.options(
            joinedload(ReviewCycle.question).joinedload(Question.topic)
        )

    def get_by_id(self, cycle_id: int) -> ReviewCycle | None:
        return self._with_question().filter(ReviewCycle.id == cycle_id).first()

    def get_active(self, user_id: int, question_id: int) -> ReviewCycle | None:
        return ReviewCycle.query.filter_by(
            user_id=user_id, question_id=question_id, status="active"
        ).first()

    def list_due(self, user_id: int, day) -> list[ReviewCycle]:
        return (
            self._with_question()
            .filter(
                ReviewCycle.user_id == user_id,
                ReviewCycle.status == "active",
                ReviewCycle.due_date <= day,
            )
            .all()
        )

    def due_counts_by_topic(self, user_id: int, day) -> dict[int, int]:
        rows = (
            ReviewCycle.query.join(Question, ReviewCycle.question_id == Question.id)
            .filter(
                ReviewCycle.user_id == user_id,
                ReviewCycle.status == "active",
                ReviewCycle.due_date <= day,
                Question.topic_id.isnot(None),
            )
            .with_entities(Question.topic_id, func.count(ReviewCycle.id))
            .group_by(Question.topic_id)
            .all()
        )
        return {int(topic_id): int(count) for topic_id, count in rows}

    def count_due(self, user_id: int, day) -> int:
        return ReviewCycle.query.filter(
            ReviewCycle.user_id == user_id,
            ReviewCycle.status == "active",
            ReviewCycle.due_date <= day,
        ).count()

    def count_overdue(self, user_id: int, day) -> int:
        return ReviewCycle.query.filter(
            ReviewCycle.user_id == user_id,
            ReviewCycle.status == "active",
            ReviewCycle.due_date < day,
        ).count()

    def list_between(self, user_id: int, start, end) -> list[ReviewCycle]:
        return ReviewCycle.query.filter(
            ReviewCycle.user_id == user_id,
            ReviewCycle.status == "active",
            ReviewCycle.due_date >= start,
            ReviewCycle.due_date <= end,
        ).all()

    def list_for_question(self, user_id: int, question_id: int) -> list[ReviewCycle]:
        return (
            ReviewCycle.query.filter_by(user_id=user_id, question_id=question_id)
            .order_by(ReviewCycle.id.asc())
            .all()
        )

    def list_active_by_question(self, question_id: int) -> list[ReviewCycle]:
        return ReviewCycle.query.filter_by(question_id=question_id, status="active").all()

    def events_for(self, cycle_id: int) -> list[ReviewEvent]:
        return (
            ReviewEvent.query.filter_by(cycle_id=cycle_id)
            .order_by(ReviewEvent.occurred_at.asc(), ReviewEvent.id.asc())
            .all()
        )

    def add_event(self, event: ReviewEvent) -> ReviewEvent:
        return self.add(event)
