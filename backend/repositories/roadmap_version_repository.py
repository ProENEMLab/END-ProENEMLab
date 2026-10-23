import json

from extensions import db
from models.roadmap import RoadmapVersion, RoadmapVersionTopic, UserNotice
from models.topic import UserTopicProgress
from repositories.base_repository import BaseRepository

class RoadmapVersionRepository(BaseRepository):

    model = RoadmapVersion

    def get_active(self) -> RoadmapVersion | None:
        return RoadmapVersion.query.filter_by(status="active").first()

    def list_versions(self) -> list[RoadmapVersion]:
        return RoadmapVersion.query.order_by(RoadmapVersion.id.desc()).all()

    def topics_for(self, version_id: int) -> list[RoadmapVersionTopic]:
        return (
            RoadmapVersionTopic.query.filter_by(version_id=version_id)
            .order_by(RoadmapVersionTopic.position.asc())
            .all()
        )

    def user_ids_with_progress(self) -> list[int]:
        rows = db.session.query(UserTopicProgress.user_id).distinct().all()
        return [row[0] for row in rows]

    def unseen_notice(self, user_id: int, kind: str) -> UserNotice | None:
        return (
            UserNotice.query.filter_by(user_id=user_id, kind=kind, seen_at=None)
            .order_by(UserNotice.id.desc())
            .first()
        )

    def unseen_notices(self, user_id: int) -> list[UserNotice]:
        return (
            UserNotice.query.filter_by(user_id=user_id, kind="roadmap_updated", seen_at=None)
            .order_by(UserNotice.id.desc())
            .all()
        )

    def get_notice(self, notice_id: int) -> UserNotice | None:
        return db.session.get(UserNotice, notice_id)

    def add_notice(self, notice: UserNotice) -> UserNotice:
        self.add(notice)
        return notice

def dump_json(value) -> str:
    return json.dumps(value, ensure_ascii=False)
