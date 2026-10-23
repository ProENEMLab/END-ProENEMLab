from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.progression_service import ProgressionService
from services.questions_service import QuestionsService
from services.subject_names import normalize_subject
from views.parsing import parse_json
from views.question_schemas import (
    AnswerSchema,
    AttemptOutputSchema,
    QuestionListSchema,
    QuestionPublicSchema,
)
from views.responses import success, validation_error

class QuestionController:

    def __init__(
        self,
        questions_service: QuestionsService,
        progression_service: ProgressionService | None = None,
    ) -> None:
        self.service = questions_service
        self.progression = progression_service
        self.answer_schema = AnswerSchema()
        self.list_output = QuestionListSchema()
        self.public_output = QuestionPublicSchema()
        self.attempt_output = AttemptOutputSchema()

    def list_questions(self):
        payload = self.service.list_questions(**self._list_kwargs())
        return success(self.list_output.dump(payload), 200)

    def count_questions(self):
        payload = self.service.list_questions(**self._list_kwargs(count_only=True))
        return success(self.list_output.dump(payload), 200)

    def questions_meta(self):
        return success(self.service.list_meta(), 200)

    def get_question(self, question_id: int):
        question = self.service.get_question(question_id)
        return success({"question": self.public_output.dump(question)}, 200)

    def answer_question(self, question_id: int):
        try:
            data = parse_json(self.answer_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        user_id = current_user_id()
        result = self.service.answer_question(user_id, question_id, data["selected_option"])
        if self.progression:
            self.progression.on_attempt(user_id, question_id)
        return success(result, 200)

    def list_attempts(self):
        attempts = self.service.list_attempts(current_user_id())
        return success({"attempts": self.attempt_output.dump(attempts, many=True)}, 200)

    def _list_kwargs(self, *, count_only: bool = False) -> dict:
        kwargs = {
            "years": _or_none(_int_list("year", "years")),
            "subjects": _or_none(_subject_params()),
            "topic_ids": _or_none(_int_list("topic_id", "topic_ids")),
            "languages": _or_none(_str_list("idioma", "language", "languages")),
            "difficulty": _text_arg("difficulty"),
            "exclude_answered_user_id": _answered_user(),
            "count_only": count_only,
        }
        if count_only:
            return kwargs
        kwargs["page"] = _page()
        kwargs["per_page"] = request.args.get("per_page", default=20, type=int)
        return kwargs

def _or_none(values):
    if values:
        return values
    return None

def _subject_params():
    subjects = []
    for item in _str_list("disciplina", "subject", "subjects"):
        subjects.append(_subject_param(item))
    return subjects

def _subject_param(item):
    normalized = normalize_subject(item)
    if normalized:
        return normalized
    return item

def _text_arg(name):
    value = request.args.get(name)
    if value:
        return value
    return None

def _answered_user():
    if _truthy("exclude_answered"):
        return current_user_id()
    if _truthy("excluir_respondidas"):
        return current_user_id()
    return None

def _int_list(*keys: str) -> list[int]:
    values: list[int] = []
    for key in keys:
        for raw in request.args.getlist(key):
            for part in str(raw).split(","):
                part = part.strip()
                if part.lstrip("-").isdigit():
                    values.append(int(part))
    return list(dict.fromkeys(values))

def _str_list(*keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        for raw in request.args.getlist(key):
            for part in str(raw).split(","):
                part = part.strip()
                if part:
                    values.append(part)
    return list(dict.fromkeys(values))

def _truthy(key: str) -> bool:
    return str(request.args.get(key, "")).lower() in {"1", "true", "yes", "on"}

def _page() -> int:
    page = request.args.get("pagina", type=int)
    if page is None:
        page = request.args.get("page", default=1, type=int)
    return page

from flask import Blueprint
from flask_jwt_extended import jwt_required

questions_bp = Blueprint("questions", __name__)

def bind_question_routes() -> None:
    if getattr(bind_question_routes, "done", False):
        return
    bind_question_routes.done = True
    from container import enem_controller, question_controller
    _list_questions = jwt_required()(question_controller.list_questions)
    _count_questions = jwt_required()(question_controller.count_questions)
    _questions_meta = jwt_required()(question_controller.questions_meta)
    _get_question = jwt_required()(question_controller.get_question)
    _answer_question = jwt_required()(question_controller.answer_question)

    questions_bp.get("/api/questions")(_list_questions)
    questions_bp.get("/api/questoes")(_list_questions)
    questions_bp.get("/api/questions/count")(_count_questions)
    questions_bp.get("/api/questoes/count")(_count_questions)
    questions_bp.get("/api/questions/meta")(_questions_meta)
    questions_bp.get("/api/questoes/meta")(_questions_meta)
    questions_bp.get("/api/questions/<int:question_id>")(_get_question)
    questions_bp.get("/api/questoes/<int:question_id>")(_get_question)
    questions_bp.post("/api/questions/<int:question_id>/answer")(_answer_question)
    questions_bp.post("/api/questoes/<int:question_id>/answer")(_answer_question)
    questions_bp.get("/api/attempts")(jwt_required()(question_controller.list_attempts))
    questions_bp.post("/api/questoes/sync")(jwt_required()(enem_controller.sync))
