from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.stats_service import StatsService
from views.parsing import parse_json
from views.question_schemas import AttemptOutputSchema
from views.responses import success, validation_error
from views.stats_schemas import ErrorTypeSchema

class StatsController:

    def __init__(self, stats_service: StatsService) -> None:
        self.service = stats_service
        self.error_schema = ErrorTypeSchema()
        self.attempt_output = AttemptOutputSchema()

    def performance(self):
        return success(self.service.get_performance(current_user_id()), 200)

    def set_error_type(self, attempt_id: int):
        try:
            data = parse_json(self.error_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        attempt = self.service.set_error_type(current_user_id(), attempt_id, data["error_type"])
        return success({"attempt": self.attempt_output.dump(attempt)}, 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

stats_bp = Blueprint("stats", __name__)

def bind_stats_routes() -> None:
    if getattr(bind_stats_routes, "done", False):
        return
    bind_stats_routes.done = True
    from container import stats_controller
    stats_bp.get("/api/stats/performance")(jwt_required()(stats_controller.performance))
    stats_bp.patch("/api/attempts/<int:attempt_id>/error-type")(
        jwt_required()(stats_controller.set_error_type)
    )
