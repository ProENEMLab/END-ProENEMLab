from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.goals_service import GoalsService
from views.goal_schemas import GoalCreateSchema, GoalOutputSchema
from views.parsing import parse_date_arg, parse_json
from views.responses import success, validation_error

class GoalController:

    def __init__(self, goals_service: GoalsService) -> None:
        self.service = goals_service
        self.create_schema = GoalCreateSchema()
        self.output = GoalOutputSchema()

    def list_goals(self):
        try:
            target_date = parse_date_arg(request.args.get("date"))
        except ValidationError as err:
            return validation_error(err, as_text=True)
        goals = self.service.list_goals(current_user_id(), target_date)
        return success({"goals": self.output.dump(goals, many=True)}, 200)

    def create_goal(self):
        try:
            data = parse_json(self.create_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        goal = self.service.create_goal(current_user_id(), data["description"], data["target_date"])
        return success({"goal": self.output.dump(goal)}, 201)

    def complete_goal(self, goal_id: int):
        goal = self.service.complete_goal(current_user_id(), goal_id)
        return success({"goal": self.output.dump(goal)}, 200)

    def delete_goal(self, goal_id: int):
        self.service.delete_goal(current_user_id(), goal_id)
        return success({"message": "Goal deleted."}, 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

goals_bp = Blueprint("goals", __name__, url_prefix="/api/goals")

def bind_goal_routes() -> None:
    if getattr(bind_goal_routes, "done", False):
        return
    bind_goal_routes.done = True
    from container import goal_controller
    goals_bp.get("")(jwt_required()(goal_controller.list_goals))
    goals_bp.post("")(jwt_required()(goal_controller.create_goal))
    goals_bp.patch("/<int:goal_id>/complete")(jwt_required()(goal_controller.complete_goal))
    goals_bp.delete("/<int:goal_id>")(jwt_required()(goal_controller.delete_goal))
