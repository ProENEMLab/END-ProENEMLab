from models.saved_filter import SavedFilterSet
from repositories.base_repository import BaseRepository

class FilterRepository(BaseRepository):

    model = SavedFilterSet

    def list_by_user(self, user_id: int) -> list[SavedFilterSet]:
        return (
            SavedFilterSet.query.filter_by(user_id=user_id)
            .order_by(SavedFilterSet.updated_at.desc())
            .all()
        )

    def get_by_name(self, user_id: int, name: str) -> SavedFilterSet | None:
        return SavedFilterSet.query.filter_by(user_id=user_id, name=name).first()
