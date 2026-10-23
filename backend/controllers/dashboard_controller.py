from controllers.http import current_user_id
from services.dashboard_service import DashboardService
from views.responses import success

class DashboardController:

    def __init__(self, dashboard_service: DashboardService) -> None:
        self.service = dashboard_service

    def get_dashboard(self):
        return success(self.service.get_dashboard(current_user_id()), 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

def bind_dashboard_routes() -> None:
    if getattr(bind_dashboard_routes, "done", False):
        return
    bind_dashboard_routes.done = True
    from container import dashboard_controller
    dashboard_bp.get("")(jwt_required()(dashboard_controller.get_dashboard))
