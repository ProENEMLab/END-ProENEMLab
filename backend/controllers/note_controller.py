from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.notes_service import NotesService
from views.note_schemas import NoteCreateSchema, NoteOutputSchema, NoteUpdateSchema
from views.parsing import parse_json
from views.responses import success, validation_error

class NoteController:

    def __init__(self, note_service: NotesService) -> None:
        self.service = note_service
        self.create_schema = NoteCreateSchema()
        self.update_schema = NoteUpdateSchema()
        self.output = NoteOutputSchema()

    def list_notes(self, topic_id: int):
        notes = self.service.list_notes(current_user_id(), topic_id)
        return success({"notes": self.output.dump(notes, many=True)}, 200)

    def create_note(self, topic_id: int):
        try:
            data = parse_json(self.create_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err, with_code=False)
        note = self.service.create_note(current_user_id(), topic_id, data["content"])
        return success({"note": self.output.dump(note)}, 201)

    def update_note(self, note_id: int):
        try:
            data = parse_json(self.update_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err, with_code=False)
        note = self.service.update_note(current_user_id(), note_id, data["content"])
        return success({"note": self.output.dump(note)}, 200)

    def delete_note(self, note_id: int):
        self.service.delete_note(current_user_id(), note_id)
        return success({"message": "Note deleted."}, 200)

from flask import Blueprint
from flask_jwt_extended import jwt_required

notes_bp = Blueprint("notes", __name__)

def bind_note_routes() -> None:
    if getattr(bind_note_routes, "done", False):
        return
    bind_note_routes.done = True
    from container import note_controller
    notes_bp.get("/api/topics/<int:topic_id>/notes")(jwt_required()(note_controller.list_notes))
    notes_bp.post("/api/topics/<int:topic_id>/notes")(jwt_required()(note_controller.create_note))
    notes_bp.put("/api/notes/<int:note_id>")(jwt_required()(note_controller.update_note))
    notes_bp.delete("/api/notes/<int:note_id>")(jwt_required()(note_controller.delete_note))
