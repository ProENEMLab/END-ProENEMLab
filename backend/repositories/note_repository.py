from models.note import Note
from repositories.base_repository import BaseRepository

class NoteRepository(BaseRepository):

    model = Note

    def list_for_topic(self, user_id: int, topic_id: int) -> list[Note]:
        return (
            Note.query.filter_by(user_id=user_id, topic_id=topic_id)
            .order_by(Note.updated_at.desc())
            .all()
        )
