from datetime import datetime, timezone

from services.exceptions import QuestionsError
from models.attempt import Attempt
from models.question import SOURCE_ATTRIBUTION, Question
from repositories.attempt_repository import AttemptRepository
from repositories.question_repository import QuestionRepository
from services.points_service import PointsService
from services.streak_service import StreakService
from services.subject_names import normalize_subject

POINTS_AWARDED_IN_RESPONSE = 5
RECENT_WRONG_THRESHOLD = 2

class QuestionsService:

    def __init__(
        self,
        question_repository: QuestionRepository,
        attempt_repository: AttemptRepository,
        points_service: PointsService,
        streak_service: StreakService,
        review_service=None,
    ) -> None:
        self.questions = question_repository
        self.attempts = attempt_repository
        self.points = points_service
        self.streak = streak_service
        self.reviews = review_service

    def list_questions(
        self,
        year: int | None = None,
        subject: str | None = None,
        topic_id: int | None = None,
        language: str | None = None,
        years: list[int] | None = None,
        subjects: list[str] | None = None,
        topic_ids: list[int] | None = None,
        languages: list[str] | None = None,
        difficulty: str | None = None,
        page: int = 1,
        per_page: int = 20,
        exclude_answered_user_id: int | None = None,
        count_only: bool = False,
    ) -> dict:
        page = max(page, 1)
        per_page = min(max(per_page, 1), 100)
        query = self._filtered_query(
            year,
            subject,
            topic_id,
            language,
            years,
            subjects,
            topic_ids,
            languages,
            difficulty,
            exclude_answered_user_id,
        )
        if count_only:
            return {"total": query.count()}
        return self._page(query, page, per_page)

    def list_meta(self) -> dict:
        return self.questions.list_meta()

    def get_question(self, question_id: int) -> Question:
        question = self.questions.get_by_id(question_id)
        if not question:
            raise QuestionsError("Question not found.", 404, "QUESTION_NOT_FOUND")
        return question

    def answer_question(
        self,
        user_id: int,
        question_id: int,
        selected_option: str,
        context: str = "bank",
    ) -> dict:
        question = self.questions.get_by_id(question_id)
        if not question:
            raise QuestionsError("Question not found.", 404, "QUESTION_NOT_FOUND")

        letter = self._require_letter(selected_option)
        is_correct = letter == question.correct_option.upper()
        attempt = self._save_attempt(user_id, question, letter, is_correct)
        suggested = self._suggested_action(user_id, question, is_correct)
        self.attempts.commit()
        if self.reviews is not None:
            self.reviews.on_attempt(
                user_id, question.id, is_correct, context, attempt_id=attempt.id
            )
        return self._answer_payload(question, attempt, is_correct, suggested)

    def _require_letter(self, selected_option: str) -> str:
        letter = selected_option.strip().upper()
        if letter not in {"A", "B", "C", "D", "E"}:
            raise QuestionsError(
                "selected_option must be one of A–E.",
                400,
                "INVALID_OPTION",
            )
        return letter

    def _save_attempt(
        self, user_id: int, question: Question, letter: str, is_correct: bool
    ) -> Attempt:
        attempt = Attempt(
            user_id=user_id,
            question_id=question.id,
            selected_option=letter,
            is_correct=is_correct,
            answered_at=datetime.now(timezone.utc),
        )
        self.attempts.add(attempt)
        self.attempts.flush()
        self.points.award_points(
            user_id, "question_answered", reference_id=attempt.id, commit=False
        )
        self.streak.register_activity(user_id, commit=False)
        return attempt

    def list_attempts(self, user_id: int) -> list[Attempt]:
        return self.attempts.list_by_user(user_id)

    def _filtered_query(
        self,
        year,
        subject,
        topic_id,
        language,
        years,
        subjects,
        topic_ids,
        languages,
        difficulty,
        exclude_answered_user_id,
    ):
        filters = self._collect_filters(
            year, subject, topic_id, language, years, subjects, topic_ids, languages
        )
        return self.questions.apply_filters(
            self.questions.base_query(),
            years=filters["years"],
            subjects=filters["subjects"],
            topic_ids=filters["topic_ids"],
            languages=filters["languages"],
            difficulties=self._difficulty_filter(difficulty),
            exclude_answered_user_id=exclude_answered_user_id,
        )

    def _page(self, query, page: int, per_page: int) -> dict:
        pagination = self.questions.paginate(query, page, per_page)
        attribution = SOURCE_ATTRIBUTION if self.questions.has_enem_cache() else None
        return {
            "items": pagination.items,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
            "attribution": attribution,
        }

    def _collect_filters(
        self,
        year,
        subject,
        topic_id,
        language,
        years,
        subjects,
        topic_ids,
        languages,
    ) -> dict:
        years = _copy_with(years, year, keep_empty=True)
        subjects = _copy_with(subjects, _subject_value(subject))
        topic_ids = _copy_with(topic_ids, topic_id, keep_empty=True)
        languages = _copy_with(languages, language)
        return {
            "years": _dedupe(years),
            "subjects": _dedupe_present(subjects),
            "topic_ids": _dedupe(topic_ids),
            "languages": _dedupe_present(languages),
        }

    def _difficulty_filter(self, difficulty: str | None) -> list[str] | None:
        if not difficulty:
            return None
        if difficulty not in {"easy", "medium", "hard"}:
            raise QuestionsError(
                "difficulty must be easy, medium or hard.",
                400,
                "INVALID_DIFFICULTY",
            )
        return [difficulty]

    def _suggested_action(self, user_id: int, question: Question, is_correct: bool) -> dict:
        if not is_correct:
            return {
                "id": "explanation",
                "label": "Ver gabarito e comentário",
                "subject": question.subject,
            }
        recent = self.attempts.recent_for_subject(user_id, question.subject)
        prior_wrong = sum(1 for attempt in recent[1:4] if not attempt.is_correct)
        if prior_wrong >= RECENT_WRONG_THRESHOLD:
            return {
                "id": "subject_stats",
                "label": f"Ver desempenho em {question.subject}",
                "subject": question.subject,
            }
        return {
            "id": "next_question",
            "label": "Próxima questão",
            "subject": question.subject,
        }

    def _answer_payload(self, question, attempt, is_correct: bool, suggested: dict) -> dict:
        return {
            "is_correct": is_correct,
            "correct_option": question.correct_option,
            "explanation_text": question.explanation_text,
            "explanation_image_url": question.explanation_image_url,
            "explanation_video_url": question.explanation_video_url,
            "points_awarded": POINTS_AWARDED_IN_RESPONSE,
            "attempt_id": attempt.id,
            "subject": question.subject,
            "suggested_action": suggested,
        }

def _copy_with(values, extra, keep_empty=False):
    items = list(values or [])
    if keep_empty and extra is not None:
        items.append(extra)
    elif extra:
        items.append(extra)
    return items

def _subject_value(subject):
    if not subject:
        return None
    return normalize_subject(subject) or subject

def _dedupe(items):
    if not items:
        return None
    return list(dict.fromkeys(items))

def _dedupe_present(items):
    kept = []
    for item in items:
        if item and item not in kept:
            kept.append(item)
    if not kept:
        return None
    return kept
