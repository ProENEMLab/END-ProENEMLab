from controllers.http import current_user_id
from services.streak_service import StreakService
from views.responses import success

class StreakController:

    def __init__(self, streak_service: StreakService) -> None:
        self.service = streak_service

    def get_streak(self):
        return success(self.service.get_current(current_user_id()), 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

streak_bp = Blueprint("streak", __name__, url_prefix="/api/streak")

def bind_streak_routes() -> None:
    if getattr(bind_streak_routes, "done", False):
        return
    bind_streak_routes.done = True
    from container import streak_controller
    streak_bp.get("")(jwt_required()(streak_controller.get_streak))
