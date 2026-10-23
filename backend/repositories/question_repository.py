from sqlalchemy import or_

from extensions import db
from models.attempt import Attempt
from models.question import SOURCE_ATTRIBUTION, Question
from models.topic import Topic
from repositories.base_repository import BaseRepository
from services.subject_names import normalize_subject

class QuestionRepository(BaseRepository):

    model = Question

    def has_enem_cache(self) -> bool:
        return db.session.query(Question.id).filter_by(source="enem-api").first() is not None

    def base_query(self):
        query = Question.query
        if self.has_enem_cache():
            query = query.filter(Question.source == "enem-api")
        return query

    def apply_filters(
        self,
        query,
        *,
        years: list[int] | None = None,
        subjects: list[str] | None = None,
        topic_ids: list[int] | None = None,
        languages: list[str] | None = None,
        difficulties: list[str] | None = None,
        exclude_answered_user_id: int | None = None,
    ):
        if years:
            query = query.filter(Question.year.in_(years))
        if subjects:
            normalized = [normalize_subject(subject) or subject for subject in subjects]
            query = query.filter(Question.subject.in_(normalized))
        if topic_ids:
            query = query.filter(Question.topic_id.in_(topic_ids))
        if languages:
            query = query.filter(Question.language.in_(languages))
        if difficulties:
            query = query.filter(Question.difficulty.in_(difficulties))
        if exclude_answered_user_id:
            answered = (
                db.session.query(Attempt.question_id)
                .filter(Attempt.user_id == exclude_answered_user_id)
                .distinct()
            )
            query = query.filter(Question.id.notin_(answered))
        return query

    def paginate(self, query, page: int, per_page: int):
        ordered = query.order_by(Question.year.desc(), Question.enem_index.asc(), Question.id.asc())
        return ordered.paginate(page=page, per_page=per_page, error_out=False)

    def list_meta(self) -> dict:
        query = self.base_query()
        years = [
            row[0]
            for row in query.with_entities(Question.year)
            .distinct()
            .order_by(Question.year.desc())
            .all()
        ]
        subjects = [
            row[0]
            for row in query.with_entities(Question.subject)
            .distinct()
            .order_by(Question.subject.asc())
            .all()
        ]
        languages = [
            row[0]
            for row in query.with_entities(Question.language)
            .filter(Question.language.isnot(None), Question.language != "")
            .distinct()
            .order_by(Question.language.asc())
            .all()
        ]
        topic_rows = (
            query.with_entities(Question.topic_id, Topic.name, Topic.subject)
            .join(Topic, Question.topic_id == Topic.id)
            .filter(Question.topic_id.isnot(None))
            .distinct()
            .order_by(Topic.name.asc())
            .all()
        )
        topics = [
            {"id": topic_id, "name": name, "subject": subject}
            for topic_id, name, subject in topic_rows
            if topic_id is not None
        ]
        return {
            "years": years,
            "subjects": subjects,
            "languages": languages,
            "topics": topics,
            "attribution": SOURCE_ATTRIBUTION if self.has_enem_cache() else None,
        }

    def list_all(self) -> list[Question]:
        return Question.query.order_by(Question.id.asc()).all()

    def list_for_linking(self, year: int | None = None) -> list[Question]:
        query = Question.query.order_by(Question.id.asc())
        if year is not None:
            query = query.filter(Question.year == year)
        return query.all()

    def count_with_difficulty(self, topic_id: int, level: str) -> int:
        return Question.query.filter_by(topic_id=topic_id, difficulty=level).count()

    def list_for_topic_level(self, topic_id: int, level: str) -> list[Question]:
        return (
            Question.query.filter(
                Question.topic_id == topic_id,
                or_(Question.difficulty == level, Question.difficulty.is_(None)),
            )
            .order_by(Question.enem_index.asc(), Question.id.asc())
            .all()
        )

    def list_by_years(self, years: list[int]) -> list[Question]:
        if not years:
            return []
        return Question.query.filter(Question.year.in_(years)).order_by(Question.id.asc()).all()

    def find_enem(self, year: int, enem_index: int, language: str) -> Question | None:
        return Question.query.filter_by(
            year=year,
            enem_index=enem_index,
            language=language,
            source="enem-api",
        ).first()
