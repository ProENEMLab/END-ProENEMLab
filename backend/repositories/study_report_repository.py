from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import aliased

from extensions import db
from models.attempt import Attempt
from models.learning import ReviewCycle
from models.note import Note
from models.question import Question, QuestionOption
from models.roadmap import RoadmapVersion, RoadmapVersionTopic
from models.subject import Subject
from models.topic import Topic, UserTopicProgress
from repositories.base_repository import BaseRepository

def _naive(value):
    if value is not None and getattr(value, "tzinfo", None) is not None:
        return value.replace(tzinfo=None)
    return value

class StudyReportRepository(BaseRepository):

    model = Note

    def get_subject(self, subject_id: int) -> Subject | None:
        return db.session.get(Subject, subject_id)

    def roadmap_positions(self) -> list[tuple[int, int]]:
        active = RoadmapVersion.query.filter_by(status="active").first()
        ordered: list[tuple[int, int]] = []
        known: set[int] = set()
        if active is not None:
            rows = (
                RoadmapVersionTopic.query.filter_by(version_id=active.id)
                .order_by(RoadmapVersionTopic.position.asc(), RoadmapVersionTopic.topic_id.asc())
                .all()
            )
            for index, row in enumerate(rows, start=1):
                ordered.append((row.topic_id, index))
                known.add(row.topic_id)
        extras = Topic.query.order_by(Topic.order_index.asc(), Topic.id.asc()).all()
        next_position = len(ordered) + 1
        for topic in extras:
            if topic.id in known:
                continue
            ordered.append((topic.id, next_position))
            known.add(topic.id)
            next_position += 1
        return ordered

    def progress_by_topic(self, user_id: int) -> dict[int, str]:
        rows = UserTopicProgress.query.filter_by(user_id=user_id).all()
        return {row.topic_id: row.status for row in rows}

    def list_notes(
        self,
        user_id: int,
        subject_name: str | None,
        start: datetime | None,
        end: datetime | None,
    ) -> list[Note]:
        query = Note.query.filter(Note.user_id == user_id).join(Topic, Note.topic_id == Topic.id)
        if subject_name:
            query = query.filter(Topic.subject == subject_name)
        if start or end:
            created = Note.created_at.isnot(None)
            updated = Note.updated_at.isnot(None)
            if start:
                created = created & (Note.created_at >= _naive(start))
                updated = updated & (Note.updated_at >= _naive(start))
            if end:
                created = created & (Note.created_at < _naive(end))
                updated = updated & (Note.updated_at < _naive(end))
            query = query.filter(db.or_(created, updated))
        return query.order_by(Note.created_at.asc(), Note.id.asc()).all()

    def list_wrong_questions(
        self,
        user_id: int,
        subject_name: str | None,
        start: datetime | None,
        end: datetime | None,
        include_resolved: bool,
    ) -> list[dict]:
        wrongs = Attempt.query.filter(Attempt.user_id == user_id, Attempt.is_correct.is_(False))
        if start:
            wrongs = wrongs.filter(Attempt.answered_at >= _naive(start))
        if end:
            wrongs = wrongs.filter(Attempt.answered_at < _naive(end))
        in_period = wrongs.with_entities(Attempt.question_id).distinct().subquery()

        last_wrong = (
            db.session.query(
                Attempt.question_id.label("question_id"),
                func.max(Attempt.answered_at).label("last_wrong_at"),
            )
            .filter(Attempt.user_id == user_id, Attempt.is_correct.is_(False))
            .group_by(Attempt.question_id)
            .subquery()
        )
        last_attempt_id = (
            db.session.query(
                Attempt.question_id.label("question_id"),
                func.max(Attempt.id).label("attempt_id"),
            )
            .join(
                last_wrong,
                (Attempt.question_id == last_wrong.c.question_id)
                & (Attempt.answered_at == last_wrong.c.last_wrong_at)
                & (Attempt.is_correct.is_(False))
                & (Attempt.user_id == user_id),
            )
            .group_by(Attempt.question_id)
            .subquery()
        )
        last_attempt = aliased(Attempt)
        resolved = (
            db.session.query(
                Attempt.question_id.label("question_id"),
                func.min(Attempt.answered_at).label("resolved_at"),
            )
            .join(last_wrong, Attempt.question_id == last_wrong.c.question_id)
            .filter(
                Attempt.user_id == user_id,
                Attempt.is_correct.is_(True),
                Attempt.answered_at > last_wrong.c.last_wrong_at,
            )
            .group_by(Attempt.question_id)
            .subquery()
        )
        counts = (
            db.session.query(
                Attempt.question_id.label("question_id"),
                func.count(Attempt.id).label("attempt_count"),
            )
            .filter(Attempt.user_id == user_id)
            .group_by(Attempt.question_id)
            .subquery()
        )
        latest_cycle = (
            db.session.query(
                ReviewCycle.question_id.label("question_id"),
                func.max(ReviewCycle.id).label("cycle_id"),
            )
            .filter(ReviewCycle.user_id == user_id)
            .group_by(ReviewCycle.question_id)
            .subquery()
        )
        cycle = aliased(ReviewCycle)
        query = (
            db.session.query(
                Question,
                Topic,
                last_attempt.selected_option,
                last_attempt.answered_at,
                resolved.c.resolved_at,
                counts.c.attempt_count,
                cycle.status,
            )
            .join(in_period, Question.id == in_period.c.question_id)
            .join(last_attempt_id, Question.id == last_attempt_id.c.question_id)
            .join(last_attempt, last_attempt.id == last_attempt_id.c.attempt_id)
            .outerjoin(Topic, Topic.id == Question.topic_id)
            .outerjoin(resolved, resolved.c.question_id == Question.id)
            .outerjoin(counts, counts.c.question_id == Question.id)
            .outerjoin(latest_cycle, latest_cycle.c.question_id == Question.id)
            .outerjoin(cycle, cycle.id == latest_cycle.c.cycle_id)
        )
        if subject_name:
            query = query.filter(Question.subject == subject_name)
        if not include_resolved:
            query = query.filter(resolved.c.resolved_at.is_(None))
        rows = []
        for (
            question,
            topic,
            selected,
            answered_at,
            resolved_at,
            attempt_count,
            review_status,
        ) in query.all():
            rows.append(
                {
                    "question": question,
                    "topic": topic,
                    "selected_option": selected,
                    "last_wrong_at": answered_at,
                    "resolved_at": resolved_at,
                    "attempt_count": int(attempt_count or 0),
                    "review_status": review_status,
                }
            )
        return rows

    def options_for(self, question_ids: list[int]) -> dict[int, list[QuestionOption]]:
        grouped: dict[int, list[QuestionOption]] = {}
        if not question_ids:
            return grouped
        rows = (
            QuestionOption.query.filter(QuestionOption.question_id.in_(question_ids))
            .order_by(QuestionOption.letter.asc(), QuestionOption.id.asc())
            .all()
        )
        for row in rows:
            grouped.setdefault(row.question_id, []).append(row)
        return grouped

    def attempt_totals(
        self,
        user_id: int,
        subject_name: str | None,
        start: datetime | None,
        end: datetime | None,
    ) -> tuple[int, int]:
        query = db.session.query(Attempt.is_correct).filter(Attempt.user_id == user_id)
        if subject_name:
            query = query.join(Question, Question.id == Attempt.question_id).filter(
                Question.subject == subject_name
            )
        if start:
            query = query.filter(Attempt.answered_at >= _naive(start))
        if end:
            query = query.filter(Attempt.answered_at < _naive(end))
        total = 0
        correct = 0
        for (is_correct,) in query.all():
            total += 1
            if is_correct:
                correct += 1
        return total, correct
