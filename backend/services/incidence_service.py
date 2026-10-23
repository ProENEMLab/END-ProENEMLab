from flask import current_app

from services.clock import Clock
from models.notification import InepRefresh
from repositories.insight_repository import IncidenceRepository
from repositories.topic_repository import TopicRepository

class IncidenceService:

    def __init__(
        self,
        incidence_repository: IncidenceRepository,
        topic_repository: TopicRepository,
        clock: Clock,
    ) -> None:
        self.incidence = incidence_repository
        self.topics = topic_repository
        self.clock = clock

    def current(self) -> dict:
        latest = self.incidence.latest()
        topics = self.topics.list_ordered()
        return {
            "refresh": latest.to_dict() if latest else None,
            "topics": [topic.to_dict() for topic in topics],
        }

    def refresh(self, *, force: bool = False) -> dict:
        year = self.clock.today_local().year
        existing = self.incidence.for_year(year)
        if existing and not force:
            return self.current()
        years = self._rewrite_order()
        self._store_refresh(existing, year, years)
        return self.current()

    def _rewrite_order(self):
        window = int(current_app.config["INEP_EXAM_WINDOW"])
        years = self.incidence.exam_years()[:window]
        counts = self.incidence.counts_for_years(years)
        total = sum(counts.values())
        if not total:
            total = 1
        topics = self.topics.list_ordered()
        self._apply_shares(topics, counts, total)
        self._apply_order(topics)
        return years

    def _apply_shares(self, topics, counts, total):
        for topic in topics:
            share = counts.get(topic.subject, 0) / total
            topic.inep_incidence = round(share * 100, 2)

    def _apply_order(self, topics):
        ranked = sorted(topics, key=lambda topic: (-_incidence(topic), topic.name))
        for offset, topic in enumerate(ranked):
            topic.order_index = 1000 + offset
        self.topics.flush()
        for index, topic in enumerate(ranked, start=1):
            topic.order_index = index

    def _store_refresh(self, existing, year, years):
        record = existing
        if record is None:
            record = InepRefresh(year=year, exam_years="", refreshed_at=self.clock.now_utc())
        record.exam_years = ",".join(str(item) for item in years)
        record.refreshed_at = self.clock.now_utc()
        if existing is None:
            self.incidence.add(record)
        self.incidence.commit()

def _incidence(topic) -> float:
    if topic.inep_incidence:
        return topic.inep_incidence
    return 0
