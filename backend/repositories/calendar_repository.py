from datetime import date, datetime

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from services.clock import as_utc
from extensions import db
from models.question import Question
from models.study import (
    FocusInterruption,
    FocusInterval,
    PomodoroSettings,
    StudyBlock,
    StudySession,
)
from models.subject import Subject
from models.topic import Topic
from repositories.base_repository import BaseRepository

def _naive_utc(value):
    if value is not None and getattr(value, "tzinfo", None) is not None:
        return value.replace(tzinfo=None)
    return value

class CalendarRepository(BaseRepository):

    model = StudyBlock

    def distinct_names(self) -> list[str]:
        names = {row[0] for row in Question.query.with_entities(Question.subject).distinct()}
        names.update(row[0] for row in Topic.query.with_entities(Topic.subject).distinct())
        return sorted(name for name in names if name)

    def ensure_catalog(self) -> None:
        known = {item.name for item in self.list_subjects()}
        created = False
        for name in self.distinct_names():
            if name in known:
                continue
            subject = Subject.from_name(name)
            if self.get_subject_by_name(subject.name):
                continue
            base = subject.slug
            slug = base
            suffix = 2
            while Subject.query.filter_by(slug=slug).first():
                slug = f"{base}-{suffix}"
                suffix += 1
            subject.slug = slug
            self.add(subject)
            known.add(subject.name)
            created = True
        if created:
            self.commit()

    def list_subjects(self) -> list[Subject]:
        return Subject.query.order_by(Subject.name.asc()).all()

    def get_subject(self, subject_id: int) -> Subject | None:
        return db.session.get(Subject, subject_id)

    def get_subject_by_name(self, name: str) -> Subject | None:
        return Subject.query.filter_by(name=name).first()

    def list_blocks(self, user_id: int, week_start: date) -> list[StudyBlock]:
        return (
            StudyBlock.query.filter_by(user_id=user_id, week_start=week_start)
            .order_by(StudyBlock.day_of_week.asc(), StudyBlock.start_minute.asc())
            .all()
        )

    def sessions_for_blocks(self, block_ids: list[int]) -> list[StudySession]:
        if not block_ids:
            return []
        return StudySession.query.filter(StudySession.block_id.in_(block_ids)).all()

    def detach_block(self, block_id: int) -> None:
        StudySession.query.filter_by(block_id=block_id).update({"block_id": None})

    def get_settings(self, user_id: int) -> PomodoroSettings | None:
        return db.session.get(PomodoroSettings, user_id)

    def get_session(self, session_id: int) -> StudySession | None:
        return db.session.get(StudySession, session_id)

    def open_session(self, user_id: int) -> StudySession | None:
        return (
            StudySession.query.filter(
                StudySession.user_id == user_id,
                StudySession.status.in_(("running", "paused")),
            )
            .order_by(StudySession.id.desc())
            .first()
        )

    def list_intervals(self, session_id: int) -> list[FocusInterval]:
        return (
            FocusInterval.query.filter_by(session_id=session_id)
            .order_by(FocusInterval.id.asc())
            .all()
        )

    def open_interval(self, session_id: int) -> FocusInterval | None:
        return FocusInterval.query.filter_by(session_id=session_id, ended_at=None).first()

    def sessions_between(self, user_id: int, start: datetime, end: datetime) -> list[StudySession]:
        return (
            StudySession.query.options(joinedload(StudySession.subject))
            .filter(
                StudySession.user_id == user_id,
                StudySession.started_at >= _naive_utc(start),
                StudySession.started_at < _naive_utc(end),
            )
            .order_by(StudySession.started_at.asc())
            .all()
        )

    def closed_focus_overlapping(self, user_id: int, start: datetime, end: datetime) -> list[dict]:
        rows = (
            db.session.query(
                FocusInterval.started_at,
                FocusInterval.ended_at,
                Subject.id,
                Subject.name,
            )
            .join(StudySession, FocusInterval.session_id == StudySession.id)
            .join(Subject, StudySession.subject_id == Subject.id)
            .filter(
                StudySession.user_id == user_id,
                FocusInterval.ended_at.isnot(None),
                FocusInterval.started_at < _naive_utc(end),
                FocusInterval.ended_at > _naive_utc(start),
            )
            .all()
        )
        return [
            {
                "started_at": as_utc(started_at),
                "ended_at": as_utc(ended_at),
                "subject_id": int(subject_id),
                "name": name,
            }
            for started_at, ended_at, subject_id, name in rows
        ]

    def planned_seconds(self, user_id: int, week_start: date) -> int:
        total = (
            db.session.query(func.coalesce(func.sum(StudyBlock.duration_minutes), 0))
            .filter(StudyBlock.user_id == user_id, StudyBlock.week_start == week_start)
            .scalar()
        )
        return int(total or 0) * 60

    def interruption_count(self, user_id: int, start: datetime, end: datetime) -> int:
        return (
            FocusInterruption.query.join(
                StudySession, FocusInterruption.session_id == StudySession.id
            )
            .filter(
                StudySession.user_id == user_id,
                FocusInterruption.occurred_at >= _naive_utc(start),
                FocusInterruption.occurred_at < _naive_utc(end),
            )
            .count()
        )

    def focus_seconds_between(self, user_id: int, start, end) -> int:
        rows = StudySession.query.filter(
            StudySession.user_id == user_id,
            StudySession.started_at >= _naive_utc(start),
            StudySession.started_at < _naive_utc(end),
        ).all()
        return sum(row.focused_seconds or 0 for row in rows)

    def last_event_at(self, session: StudySession) -> datetime:
        moments = [as_utc(session.started_at)]
        for interval in self.list_intervals(session.id):
            moments.append(as_utc(interval.started_at))
            if interval.ended_at is not None:
                moments.append(as_utc(interval.ended_at))
        return max(moments)
