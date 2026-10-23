from datetime import datetime, timezone

from services.exceptions import RoadmapError
from models.topic import TOPIC_STATUSES
from repositories.progress_repository import ProgressRepository
from repositories.topic_repository import TopicRepository

class RoadmapService:

    def __init__(
        self,
        topic_repository: TopicRepository,
        progress_repository: ProgressRepository,
        version_service=None,
    ) -> None:
        self.topics = topic_repository
        self.progress = progress_repository
        self.versions = version_service

    def list_roadmap(self, user_id: int) -> list[dict]:
        return self.roadmap_payload(user_id)["topics"]

    def roadmap_payload(self, user_id: int) -> dict:
        topics, version = self._decorate(self._with_status(user_id))
        return {"topics": topics, "roadmap_version": version}

    def get_next_topic(self, user_id: int) -> dict | None:
        for item in self.list_roadmap(user_id):
            if item["status"] != "completed":
                return item
        return None

    def list_notices(self, user_id: int) -> list[dict]:
        if self.versions is None:
            return []
        return self.versions.unseen_notices(user_id)

    def dismiss_notice(self, user_id: int, notice_id: int) -> dict:
        if self.versions is None:
            raise RoadmapError("Notice not found.", 404)
        notice = self.versions.dismiss_notice(user_id, notice_id)
        if notice is None:
            raise RoadmapError("Notice not found.", 404)
        return notice

    def update_topic_status(self, user_id: int, topic_id: int, status: str) -> dict:
        if status not in ("in_progress", "completed"):
            raise RoadmapError("status must be 'in_progress' or 'completed'.", 400)
        if status not in TOPIC_STATUSES:
            raise RoadmapError("Invalid status.", 400)

        topic = self.topics.get_by_id(topic_id)
        if not topic:
            raise RoadmapError("Topic not found.", 404)

        progress = self.progress.get_or_create(user_id, topic_id)
        progress.status = status
        progress.updated_at = datetime.now(timezone.utc)
        self.progress.commit()
        item = topic.to_dict()
        item["status"] = progress.status
        decorated, _version = self._decorate([item])
        return decorated[0]

    def _decorate(self, items: list[dict]) -> tuple[list[dict], dict | None]:
        version = None
        overlay = None
        if self.versions is not None:
            version = self.versions.active_summary()
            overlay = self.versions.active_incidence()
        if overlay is None:
            for item in items:
                item["incidence"] = None
            return items, None
        for item in items:
            row = overlay.get(item["id"])
            if row is None:
                item["incidence"] = None
                item["_position"] = 10**9 + item["order_index"]
            else:
                item["incidence"] = {
                    "weight": row["incidence_weight"],
                    "count": row["incidence_count"],
                    "low_incidence": row["low_incidence"],
                    "reason": row["rank_reason"],
                }
                item["_position"] = row["position"]
        items.sort(key=lambda item: (item["_position"], item["id"]))
        for item in items:
            item.pop("_position", None)
        return items, version

    def _with_status(self, user_id: int) -> list[dict]:
        topics = self.topics.list_ordered()
        progress_map = {row.topic_id: row for row in self.progress.list_by_user(user_id)}
        result = []
        for topic in topics:
            progress = progress_map.get(topic.id)
            item = topic.to_dict()
            item["status"] = progress.status if progress else "not_started"
            result.append(item)
        return result
