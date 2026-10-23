from datetime import datetime

from flask import jsonify, request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.focus_service import FocusService
from services.study_block_service import StudyBlockService
from services.study_session_service import StudySessionService
from views.calendar_schemas import (
    BlockCreateSchema,
    BlockUpdateSchema,
    InterruptionSchema,
    PomodoroSettingsSchema,
    SessionStartSchema,
)
from views.parsing import parse_date_arg, parse_json
from views.responses import error_response, success, validation_error

class CalendarController:

    def __init__(
        self,
        block_service: StudyBlockService,
        session_service: StudySessionService,
        focus_service: FocusService,
    ) -> None:
        self.blocks = block_service
        self.sessions = session_service
        self.focus = focus_service
        self.create_schema = BlockCreateSchema()
        self.update_schema = BlockUpdateSchema()
        self.settings_schema = PomodoroSettingsSchema()
        self.start_schema = SessionStartSchema()
        self.interruption_schema = InterruptionSchema()

    def list_subjects(self):
        return success({"subjects": self.blocks.list_subjects()}, 200)

    def week(self, week_start: str):
        day = self._week_day(week_start)
        if day is None:
            return error_response("week_start must be YYYY-MM-DD.", 400, "VALIDATION_ERROR")
        return success(self.blocks.week(current_user_id(), day), 200)

    def create_block(self):
        try:
            data = parse_json(self.create_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        block = self.blocks.create_block(current_user_id(), data)
        return success({"block": block}, 201)

    def update_block(self, block_id: int):
        try:
            data = parse_json(self.update_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        block = self.blocks.update_block(current_user_id(), block_id, data)
        return success({"block": block}, 200)

    def delete_block(self, block_id: int):
        self.blocks.delete_block(current_user_id(), block_id)
        return success({"message": "Block deleted."}, 200)

    def copy_previous(self, week_start: str):
        day = self._week_day(week_start)
        if day is None:
            return error_response("week_start must be YYYY-MM-DD.", 400, "VALIDATION_ERROR")
        return success(self.blocks.copy_previous_week(current_user_id(), day), 200)

    def get_settings(self):
        return success(self.blocks.get_settings(current_user_id()), 200)

    def update_settings(self):
        try:
            data = parse_json(self.settings_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        return success(self.blocks.update_settings(current_user_id(), data), 200)

    def active_session(self):
        payload = self.sessions.active(current_user_id())
        if payload is None:
            return jsonify(None), 200
        return success(payload, 200)

    def start_session(self):
        try:
            data = parse_json(self.start_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        session = self.sessions.start(current_user_id(), data)
        return success(session, 201)

    def pause_session(self, session_id: int):
        return success(self.sessions.pause(current_user_id(), session_id), 200)

    def resume_session(self, session_id: int):
        return success(self.sessions.resume(current_user_id(), session_id), 200)

    def complete_cycle(self, session_id: int):
        return success(self.sessions.complete_cycle(current_user_id(), session_id), 200)

    def finish_session(self, session_id: int):
        return success(self.sessions.finish(current_user_id(), session_id), 200)

    def focus_status(self):
        return success(self.focus.status(current_user_id()), 200)

    def create_interruption(self, session_id: int):
        try:
            data = parse_json(self.interruption_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        return success(self.focus.record_interruption(current_user_id(), session_id, data), 201)

    def list_sessions(self):
        try:
            start = parse_date_arg(request.args.get("from"))
            end = parse_date_arg(request.args.get("to"))
        except ValidationError as err:
            return validation_error(err, as_text=True)
        if start is None or end is None:
            return error_response("from and to are required.", 400, "VALIDATION_ERROR")
        sessions = self.sessions.history(current_user_id(), start, end)
        return success({"sessions": sessions}, 200)

    def _week_day(self, value: str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return None

from flask import Blueprint
from flask_jwt_extended import jwt_required

calendar_bp = Blueprint("calendar", __name__, url_prefix="/api")

def bind_calendar_routes() -> None:
    if getattr(bind_calendar_routes, "done", False):
        return
    bind_calendar_routes.done = True
    from container import calendar_controller
    calendar_bp.get("/subjects")(jwt_required()(calendar_controller.list_subjects))
    calendar_bp.get("/calendar/weeks/<week_start>")(jwt_required()(calendar_controller.week))
    calendar_bp.post("/calendar/blocks")(jwt_required()(calendar_controller.create_block))
    calendar_bp.patch("/calendar/blocks/<int:block_id>")(
        jwt_required()(calendar_controller.update_block)
    )
    calendar_bp.delete("/calendar/blocks/<int:block_id>")(
        jwt_required()(calendar_controller.delete_block)
    )
    calendar_bp.post("/calendar/weeks/<week_start>/copy-from-previous")(
        jwt_required()(calendar_controller.copy_previous)
    )
    calendar_bp.get("/pomodoro/settings")(jwt_required()(calendar_controller.get_settings))
    calendar_bp.put("/pomodoro/settings")(jwt_required()(calendar_controller.update_settings))
    calendar_bp.get("/sessions/active")(jwt_required()(calendar_controller.active_session))
    calendar_bp.get("/sessions")(jwt_required()(calendar_controller.list_sessions))
    calendar_bp.post("/sessions")(jwt_required()(calendar_controller.start_session))
    calendar_bp.post("/sessions/<int:session_id>/pause")(
        jwt_required()(calendar_controller.pause_session)
    )
    calendar_bp.post("/sessions/<int:session_id>/resume")(
        jwt_required()(calendar_controller.resume_session)
    )
    calendar_bp.post("/sessions/<int:session_id>/complete-cycle")(
        jwt_required()(calendar_controller.complete_cycle)
    )
    calendar_bp.post("/sessions/<int:session_id>/finish")(
        jwt_required()(calendar_controller.finish_session)
    )
    calendar_bp.post("/sessions/<int:session_id>/interruptions")(
        jwt_required()(calendar_controller.create_interruption)
    )
    calendar_bp.get("/focus/status")(jwt_required()(calendar_controller.focus_status))
