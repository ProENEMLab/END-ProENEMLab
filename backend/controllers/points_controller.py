from flask import request

from controllers.http import current_user_id
from services.points_service import PointsService
from views.points_schemas import PointsHistorySchema
from views.responses import success

class PointsController:

    def __init__(self, points_service: PointsService) -> None:
        self.service = points_service
        self.history_output = PointsHistorySchema()

    def get_points(self):
        total = self.service.get_total_points(current_user_id())
        return success({"total_points": total}, 200)

    def points_history(self):
        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=20, type=int)
        result = self.service.list_points_history(current_user_id(), page=page, per_page=per_page)
        return success(self.history_output.dump(result), 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

points_bp = Blueprint("points", __name__, url_prefix="/api/points")

def bind_points_routes() -> None:
    if getattr(bind_points_routes, "done", False):
        return
    bind_points_routes.done = True
    from container import points_controller
    points_bp.get("")(jwt_required()(points_controller.get_points))
    points_bp.get("/history")(jwt_required()(points_controller.points_history))
