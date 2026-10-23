from services.plans_service import PlansService
from views.responses import success

class PlansController:

    def __init__(self, plans_service: PlansService) -> None:
        self.service = plans_service

    def list_plans(self):
        return success(self.service.get_catalog(), 200)

from flask import Blueprint

plans_bp = Blueprint("plans", __name__)

def bind_plans_routes() -> None:
    if getattr(bind_plans_routes, "done", False):
        return
    bind_plans_routes.done = True
    from container import plans_controller
    plans_bp.get("/api/plans")(plans_controller.list_plans)
