from datetime import datetime, timezone

from models.topic import UserTopicProgress
from repositories.base_repository import BaseRepository

class ProgressRepository(BaseRepository):

    model = UserTopicProgress

    def list_by_user(self, user_id: int) -> list[UserTopicProgress]:
        return UserTopicProgress.query.filter_by(user_id=user_id).all()

    def get_or_create(self, user_id: int, topic_id: int) -> UserTopicProgress:
        progress = UserTopicProgress.query.filter_by(user_id=user_id, topic_id=topic_id).first()
        if progress:
            return progress
        progress = UserTopicProgress(
            user_id=user_id,
            topic_id=topic_id,
            status="not_started",
            updated_at=datetime.now(timezone.utc),
        )
        self.add(progress)
        self.commit()
        return progress
