from sqlalchemy import case, func

from extensions import db
from models.attempt import Attempt
from models.question import Question
from models.topic import Topic
from repositories.base_repository import BaseRepository

class AttemptRepository(BaseRepository):

    model = Attempt

    def list_by_user(self, user_id: int) -> list[Attempt]:
        return Attempt.query.filter_by(user_id=user_id).order_by(Attempt.answered_at.desc()).all()

    def recent_for_subject(self, user_id: int, subject: str, limit: int = 6) -> list[Attempt]:
        return (
            Attempt.query.join(Question, Attempt.question_id == Question.id)
            .filter(Attempt.user_id == user_id, Question.subject == subject)
            .order_by(Attempt.answered_at.desc())
            .limit(limit)
            .all()
        )

    def count_total_and_correct(self, user_id: int) -> tuple[int, int]:
        total = Attempt.query.filter_by(user_id=user_id).count()
        correct = Attempt.query.filter_by(user_id=user_id, is_correct=True).count()
        return total, correct

    def performance_by_topic(self, user_id: int):
        return (
            db.session.query(
                Question.topic_id,
                Topic.name,
                func.count(Attempt.id).label("total_attempts"),
                func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)).label("correct_count"),
            )
            .join(Question, Attempt.question_id == Question.id)
            .outerjoin(Topic, Question.topic_id == Topic.id)
            .filter(Attempt.user_id == user_id, Question.topic_id.isnot(None))
            .group_by(Question.topic_id, Topic.name)
            .all()
        )

    def performance_by_subject(self, user_id: int):
        return (
            db.session.query(
                Question.subject,
                func.count(Attempt.id).label("total_attempts"),
                func.sum(case((Attempt.is_correct.is_(True), 1), else_=0)).label("correct_count"),
            )
            .join(Question, Attempt.question_id == Question.id)
            .filter(Attempt.user_id == user_id)
            .group_by(Question.subject)
            .all()
        )

    def first_attempt_stats(self) -> dict[int, tuple[int, int]]:
        rows = Attempt.query.order_by(Attempt.answered_at.asc(), Attempt.id.asc()).all()
        first: dict[tuple[int, int], Attempt] = {}
        for row in rows:
            first.setdefault((row.question_id, row.user_id), row)
        stats: dict[int, tuple[int, int]] = {}
        for (question_id, _), attempt in first.items():
            users, correct = stats.get(question_id, (0, 0))
            stats[question_id] = (users + 1, correct + int(bool(attempt.is_correct)))
        return stats

    def list_wrong(self, user_id: int) -> list[Attempt]:
        return Attempt.query.filter_by(user_id=user_id, is_correct=False).all()
