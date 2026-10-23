from models.engagement import StreakRecord
from repositories.base_repository import BaseRepository

class StreakRepository(BaseRepository):

    model = StreakRecord

    def get_by_user(self, user_id: int) -> StreakRecord | None:
        return StreakRecord.query.filter_by(user_id=user_id).first()

    def get_or_create(self, user_id: int) -> StreakRecord:
        record = self.get_by_user(user_id)
        if record:
            return record
        record = StreakRecord(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            last_activity_date=None,
        )
        self.add(record)
        self.flush()
        return record
