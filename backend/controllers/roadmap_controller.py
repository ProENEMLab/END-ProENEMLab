from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.roadmap_service import RoadmapService
from views.parsing import parse_json
from views.responses import success, validation_error
from views.roadmap_schemas import TopicStatusSchema

class RoadmapController:

    def __init__(self, roadmap_service: RoadmapService) -> None:
        self.service = roadmap_service
        self.status_schema = TopicStatusSchema()

    def get_roadmap(self):
        return success(self.service.roadmap_payload(current_user_id()), 200)

    def get_next(self):
        topic = self.service.get_next_topic(current_user_id())
        if topic is None:
            return success({"topic": None, "message": "All topics completed."}, 200)
        return success({"topic": topic}, 200)

    def update_status(self, topic_id: int):
        try:
            data = parse_json(self.status_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err, with_code=False)
        topic = self.service.update_topic_status(current_user_id(), topic_id, data["status"])
        return success({"topic": topic}, 200)

    def list_notices(self):
        notices = self.service.list_notices(current_user_id())
        return success({"notices": notices}, 200)

    def see_notice(self, notice_id: int):
        notice = self.service.dismiss_notice(current_user_id(), notice_id)
        return success({"notice": notice}, 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/api/roadmap")

def bind_roadmap_routes() -> None:
    if getattr(bind_roadmap_routes, "done", False):
        return
    bind_roadmap_routes.done = True
    from container import roadmap_controller
    roadmap_bp.get("")(jwt_required()(roadmap_controller.get_roadmap))
    roadmap_bp.get("/next")(jwt_required()(roadmap_controller.get_next))
    roadmap_bp.get("/notices")(jwt_required()(roadmap_controller.list_notices))
    roadmap_bp.post("/notices/<int:notice_id>/seen")(jwt_required()(roadmap_controller.see_notice))
    roadmap_bp.patch("/topics/<int:topic_id>/status")(jwt_required()(roadmap_controller.update_status))
