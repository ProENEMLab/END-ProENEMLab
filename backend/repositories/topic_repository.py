from models.topic import Topic
from repositories.base_repository import BaseRepository

class TopicRepository(BaseRepository):

    model = Topic

    def list_ordered(self) -> list[Topic]:
        return Topic.query.order_by(Topic.order_index.asc()).all()
