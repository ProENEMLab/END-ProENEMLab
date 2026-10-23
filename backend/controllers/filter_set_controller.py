from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.filter_sets_service import FilterSetsService
from views.filter_schemas import FilterSetOutputSchema, SavedFilterSchema
from views.parsing import parse_json
from views.responses import success, validation_error

class FilterSetController:

    def __init__(self, filter_sets_service: FilterSetsService) -> None:
        self.service = filter_sets_service
        self.input_schema = SavedFilterSchema()
        self.output = FilterSetOutputSchema()

    def list_filter_sets(self):
        items = self.service.list_filter_sets(current_user_id())
        return success({"items": self.output.dump(items, many=True)}, 200)

    def save_filter_set(self):
        try:
            data = parse_json(self.input_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        item = self.service.upsert_filter_set(current_user_id(), data["name"], data["payload"])
        return success({"item": self.output.dump(item)}, 200)

    def delete_filter_set(self, filter_set_id: int):
        self.service.delete_filter_set(current_user_id(), filter_set_id)
        return success({"ok": True}, 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

filter_sets_bp = Blueprint("filter_sets", __name__)

def bind_filter_set_routes() -> None:
    if getattr(bind_filter_set_routes, "done", False):
        return
    bind_filter_set_routes.done = True
    from container import filter_set_controller
    filter_sets_bp.get("/api/filter-sets")(jwt_required()(filter_set_controller.list_filter_sets))
    filter_sets_bp.post("/api/filter-sets")(jwt_required()(filter_set_controller.save_filter_set))
    filter_sets_bp.delete("/api/filter-sets/<int:filter_set_id>")(
        jwt_required()(filter_set_controller.delete_filter_set)
    )
