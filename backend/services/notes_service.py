from datetime import datetime, timezone

from services.exceptions import NotesError
from models.note import Note
from repositories.note_repository import NoteRepository
from repositories.topic_repository import TopicRepository

class NotesService:

    def __init__(
        self,
        note_repository: NoteRepository,
        topic_repository: TopicRepository,
    ) -> None:
        self.notes = note_repository
        self.topics = topic_repository

    def list_notes(self, user_id: int, topic_id: int) -> list[Note]:
        self._require_topic(topic_id)
        return self.notes.list_for_topic(user_id, topic_id)

    def create_note(self, user_id: int, topic_id: int, content: str) -> Note:
        self._require_topic(topic_id)
        now = datetime.now(timezone.utc)
        note = Note(
            user_id=user_id,
            topic_id=topic_id,
            content=content,
            created_at=now,
            updated_at=now,
        )
        self.notes.add(note)
        self.notes.commit()
        return note

    def update_note(self, user_id: int, note_id: int, content: str) -> Note:
        note = self._require_owner(user_id, note_id, "edit")
        note.content = content
        note.updated_at = datetime.now(timezone.utc)
        self.notes.commit()
        return note

    def delete_note(self, user_id: int, note_id: int) -> None:
        note = self._require_owner(user_id, note_id, "delete")
        self.notes.delete(note)
        self.notes.commit()

    def _require_topic(self, topic_id: int) -> None:
        if not self.topics.get_by_id(topic_id):
            raise NotesError("Topic not found.", 404)

    def _require_owner(self, user_id: int, note_id: int, action: str) -> Note:
        note = self.notes.get_by_id(note_id)
        if not note:
            raise NotesError("Note not found.", 404)
        if note.user_id != user_id:
            raise NotesError(
                f"You do not have permission to {action} this note.",
                403,
            )
        return note
