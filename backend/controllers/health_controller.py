from views.responses import success

class HealthController:

    def health(self):
        return success({"status": "ok"}, 200)

from flask import Blueprint

health_bp = Blueprint("health", __name__)

def bind_health_routes() -> None:
    if getattr(bind_health_routes, "done", False):
        return
    bind_health_routes.done = True
    from container import health_controller
    health_bp.get("/api/health")(health_controller.health)
