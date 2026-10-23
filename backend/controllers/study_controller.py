from datetime import datetime

from flask import Response, request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.exceptions import ApiError, ReviewError
from services.export_service import ExportService
from services.incidence_service import IncidenceService
from services.progression_service import ProgressionService
from services.questions_service import QuestionsService
from services.report_service import WeeklyReportService
from services.review_service import ReviewService
from views.parsing import parse_json
from views.question_schemas import AnswerSchema
from views.responses import success, validation_error

class ReviewController:

    def __init__(self, review_service: ReviewService, questions_service: QuestionsService) -> None:
        self.service = review_service
        self.questions = questions_service
        self.answer_schema = AnswerSchema()

    def today(self):
        return success(self.service.today(current_user_id()), 200)

    def upcoming(self):
        raw = request.args.get("days")
        if raw is None or raw == "":
            days = 7
        elif not str(raw).isdigit():
            raise ReviewError("days must be an integer.", 400, "VALIDATION_ERROR")
        else:
            days = int(raw)
        return success(self.service.upcoming(current_user_id(), days), 200)

    def badge(self):
        return success(self.service.badge(current_user_id()), 200)

    def history(self):
        raw = request.args.get("question_id")
        if raw is None or not str(raw).isdigit():
            raise ReviewError("question_id is required.", 400, "VALIDATION_ERROR")
        return success(self.service.history(current_user_id(), int(raw)), 200)

    def detail(self, cycle_id: int):
        return success(self.service.detail(current_user_id(), cycle_id), 200)

    def answer(self, cycle_id: int):
        try:
            data = parse_json(self.answer_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        user_id = current_user_id()
        cycle = self.service.require_answerable(user_id, cycle_id)
        result = self.questions.answer_question(
            user_id,
            cycle.question_id,
            data["selected_option"],
            context="review",
        )
        result["review"] = self.service.state(cycle)
        return success(result, 200)

class ProgressionController:

    def __init__(self, progression_service: ProgressionService) -> None:
        self.service = progression_service

    def list_levels(self):
        return success({"topics": self.service.list_levels(current_user_id())}, 200)

    def topic_level(self, topic_id: int):
        return success(self.service.get_status(current_user_id(), topic_id), 200)

    def questions(self, topic_id: int):
        level = request.args.get("level") or ""
        questions = self.service.questions_for_level(current_user_id(), topic_id, level)
        return success(
            {
                "topic_id": topic_id,
                "level": level,
                "questions": [question.to_list_dict() for question in questions],
            },
            200,
        )

    def summary(self):
        return success(self.service.summary(current_user_id()), 200)

    def practice(self, topic_id: int):
        question = self.service.practice_question(current_user_id(), topic_id)
        if not question:
            return success({"question": None}, 200)
        return success({"question": question.to_public_dict()}, 200)

class ReportController:

    def __init__(self, report_service: WeeklyReportService) -> None:
        self.service = report_service

    def weekly(self):
        return success(self.service.weekly(current_user_id()), 200)

    def weekly_for(self, week_start: str):
        try:
            day = datetime.strptime(week_start, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ApiError("week_start tem que ser YYYY-MM-DD.", 400, "VALIDATION_ERROR") from exc
        return success(self.service.weekly(current_user_id(), day), 200)

    def history(self):
        raw = request.args.get("limit", "8")
        try:
            limit = int(raw)
        except (TypeError, ValueError) as exc:
            raise ApiError("limit tem que ser um inteiro.", 400, "VALIDATION_ERROR") from exc
        return success(self.service.history(current_user_id(), limit), 200)

class IncidenceController:

    def __init__(self, incidence_service: IncidenceService) -> None:
        self.service = incidence_service

    def current(self):
        return success(self.service.current(), 200)

    def refresh(self):
        force = str(request.args.get("force", "")).lower() in {"1", "true", "yes", "on"}
        return success(self.service.refresh(force=force), 200)

class ExportController:

    def __init__(self, export_service: ExportService) -> None:
        self.service = export_service

    def study_pdf(self):
        pdf = self.service.study_pdf(current_user_id())
        return Response(
            pdf,
            mimetype="application/pdf",
            headers={"Content-Disposition": "attachment; filename=proenem-estudo.pdf"},
        )

from flask import Blueprint
from flask_jwt_extended import jwt_required

review_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")
progression_bp = Blueprint("progression", __name__, url_prefix="/api/progression")
report_bp = Blueprint("reports", __name__, url_prefix="/api/reports")
incidence_bp = Blueprint("incidence", __name__, url_prefix="/api/incidence")
export_bp = Blueprint("exports", __name__, url_prefix="/api/exports")

def bind_study_routes() -> None:
    if getattr(bind_study_routes, "done", False):
        return
    bind_study_routes.done = True
    from container import (
        export_controller,
        incidence_controller,
        progression_controller,
        report_controller,
        review_controller,
    )
    review_bp.get("/today")(jwt_required()(review_controller.today))
    review_bp.get("/upcoming")(jwt_required()(review_controller.upcoming))
    review_bp.get("/badge")(jwt_required()(review_controller.badge))
    review_bp.get("/history")(jwt_required()(review_controller.history))
    review_bp.get("/<int:cycle_id>")(jwt_required()(review_controller.detail))
    review_bp.post("/<int:cycle_id>/answer")(jwt_required()(review_controller.answer))

    progression_bp.get("")(jwt_required()(progression_controller.list_levels))
    progression_bp.get("/summary")(jwt_required()(progression_controller.summary))
    progression_bp.get("/topics/<int:topic_id>")(jwt_required()(progression_controller.topic_level))
    progression_bp.get("/topics/<int:topic_id>/questions")(
        jwt_required()(progression_controller.questions)
    )
    progression_bp.get("/topics/<int:topic_id>/practice")(
        jwt_required()(progression_controller.practice)
    )

    report_bp.get("/weekly")(jwt_required()(report_controller.weekly))
    report_bp.get("/weekly/history")(jwt_required()(report_controller.history))
    report_bp.get("/weekly/<week_start>")(jwt_required()(report_controller.weekly_for))

    incidence_bp.get("")(jwt_required()(incidence_controller.current))
    incidence_bp.post("/refresh")(jwt_required()(incidence_controller.refresh))

    export_bp.get("/study.pdf")(jwt_required()(export_controller.study_pdf))
