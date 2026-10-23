import json
from datetime import date, datetime

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError

from extensions import db
from models.attempt import Attempt
from models.notification import InepRefresh
from models.question import Question
from models.study import WeeklyReport
from models.topic import Topic
from repositories.base_repository import BaseRepository

def _naive(value):
    if value is not None and getattr(value, "tzinfo", None) is not None:
        return value.replace(tzinfo=None)
    return value

class ReportRepository(BaseRepository):

    model = WeeklyReport

    def topic_stats(self, user_id: int, start: datetime, end: datetime) -> list[dict]:
        return self._topic_aggregate(user_id, start, end)

    def topic_stats_before(self, user_id: int, end: datetime) -> list[dict]:
        return self._topic_aggregate(user_id, None, end)

    def attempt_totals(self, user_id: int, start: datetime, end: datetime) -> tuple[int, int]:
        answers, correct = (
            db.session.query(func.count(Attempt.id), func.coalesce(func.sum(self._correct()), 0))
            .filter(
                Attempt.user_id == user_id,
                Attempt.answered_at >= _naive(start),
                Attempt.answered_at < _naive(end),
            )
            .one()
        )
        return int(answers or 0), int(correct or 0)

    def get_payload(self, user_id: int, week_start: date) -> dict | None:
        row = WeeklyReport.query.filter_by(user_id=user_id, week_start=week_start).first()
        if row is None:
            return None
        return json.loads(row.payload)

    def save_payload(
        self, user_id: int, week_start: date, payload: dict, generated_at: datetime
    ) -> dict:
        stored = self.get_payload(user_id, week_start)
        if stored is not None:
            return stored
        row = WeeklyReport(
            user_id=user_id,
            week_start=week_start,
            payload=json.dumps(payload, ensure_ascii=False),
            generated_at=_naive(generated_at),
        )
        try:
            self.add(row)
            self.commit()
        except IntegrityError:
            self.rollback()
            stored = self.get_payload(user_id, week_start)
            if stored is not None:
                return stored
            raise
        return payload

    def replace_payload(
        self, user_id: int, week_start: date, payload: dict, generated_at: datetime
    ) -> dict:
        encoded = json.dumps(payload, ensure_ascii=False)
        row = WeeklyReport.query.filter_by(user_id=user_id, week_start=week_start).first()
        if row is None:
            row = WeeklyReport(
                user_id=user_id,
                week_start=week_start,
                payload=encoded,
                generated_at=_naive(generated_at),
            )
            self.add(row)
        else:
            row.payload = encoded
            row.generated_at = _naive(generated_at)
        self.commit()
        return payload

    def _topic_aggregate(self, user_id: int, start: datetime | None, end: datetime) -> list[dict]:
        filters = [
            Attempt.user_id == user_id,
            Attempt.answered_at < _naive(end),
            Question.topic_id.isnot(None),
        ]
        if start is not None:
            filters.append(Attempt.answered_at >= _naive(start))
        rows = (
            db.session.query(
                Question.topic_id,
                Topic.name,
                Topic.subject,
                func.count(Attempt.id),
                func.coalesce(func.sum(self._correct()), 0),
            )
            .join(Question, Attempt.question_id == Question.id)
            .join(Topic, Question.topic_id == Topic.id)
            .filter(*filters)
            .group_by(Question.topic_id, Topic.name, Topic.subject)
            .all()
        )
        return [
            {
                "topic_id": int(topic_id),
                "name": name,
                "subject": subject,
                "answers": int(answers or 0),
                "correct": int(correct or 0),
            }
            for topic_id, name, subject, answers, correct in rows
        ]

    @staticmethod
    def _correct():
        return case((Attempt.is_correct.is_(True), 1), else_=0)

class IncidenceRepository(BaseRepository):

    model = InepRefresh

    def exam_years(self) -> list[int]:
        rows = Question.query.with_entities(Question.year).distinct().all()
        return sorted({row[0] for row in rows if row[0]}, reverse=True)

    def counts_for_years(self, years: list[int]) -> dict[str, int]:
        rows = Question.query.filter(Question.year.in_(years)).all() if years else []
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.subject] = counts.get(row.subject, 0) + 1
        return counts

    def latest(self) -> InepRefresh | None:
        return InepRefresh.query.order_by(InepRefresh.year.desc()).first()

    def for_year(self, year: int) -> InepRefresh | None:
        return InepRefresh.query.filter_by(year=year).first()
