from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from flask import current_app

from services.clock import Clock
from models.roadmap import RoadmapVersion, RoadmapVersionTopic, UserNotice
from repositories.inep_item_repository import InepItemRepository
from repositories.question_repository import QuestionRepository
from repositories.roadmap_version_repository import RoadmapVersionRepository, dump_json
from repositories.topic_repository import TopicRepository
from services.roadmap_catalog import (
    RoadmapDataError,
    index_topics,
    load_catalog,
    validate_catalog,
)
from services.roadmap_ranking import (
    compute_incidence,
    coverage_by_edition,
    edition_span,
    questions_to_slots,
    rank_topics,
)

logger = logging.getLogger(__name__)

NOTICE_KIND = "roadmap_updated"

class RoadmapVersionService:

    def __init__(
        self,
        version_repository: RoadmapVersionRepository,
        topic_repository: TopicRepository,
        question_repository: QuestionRepository,
        inep_repository: InepItemRepository,
        clock: Clock,
    ) -> None:
        self.versions = version_repository
        self.topics = topic_repository
        self.questions = question_repository
        self.inep = inep_repository
        self.clock = clock

    def build(self, reference_year: int, data_dir: str | None = None) -> dict:
        catalog = load_catalog(self._folder(data_dir))
        topics = self.topics.list_ordered()
        slug_index = index_topics(topics)
        validate_catalog(catalog, slug_index, reference_year)
        questions = self.questions.list_by_years(catalog.editions)
        abandoned = self.inep.abandoned_codes(catalog.editions)
        slots, per_year = questions_to_slots(questions, abandoned)
        skill_items, skill_map = self._skills(catalog, slug_index)
        measured = compute_incidence(
            slots,
            [topic.id for topic in topics],
            skill_items,
            skill_map,
        )
        weights = {topic_id: weight for topic_id, (_count, weight) in measured.items()}
        prerequisites = [
            (slug_index[topic].id, slug_index[prerequisite].id)
            for topic, prerequisite in catalog.prerequisites
        ]
        ranked = rank_topics(topics, weights, prerequisites, catalog.editions)
        expected = int(current_app.config["ENEM_OBJECTIVE_QUESTIONS_PER_EDITION"])
        coverage = coverage_by_edition(per_year, catalog.editions, expected)
        version = RoadmapVersion(
            reference_year=catalog.reference_year,
            editions=dump_json(catalog.editions),
            edital=catalog.edital,
            matrix_reference=catalog.matrix_reference,
            status="draft",
            coverage=dump_json({str(year): value for year, value in coverage.items()}),
            generated_at=self.clock.now_utc(),
        )
        self.versions.add(version)
        self.versions.flush()
        for row in ranked:
            count, weight = measured[row["topic_id"]]
            self.versions.add(
                RoadmapVersionTopic(
                    version_id=version.id,
                    topic_id=row["topic_id"],
                    position=row["position"],
                    incidence_count=count,
                    incidence_weight=weight,
                    low_incidence=row["low_incidence"],
                    rank_reason=row["rank_reason"],
                )
            )
        self.versions.commit()
        return self._version_payload(version)

    def scheduled_build(self, data_dir: str | None = None) -> dict:
        catalog = load_catalog(self._folder(data_dir))
        result = self.build(catalog.reference_year, data_dir=data_dir)
        logger.info(
            "Rascunho de roadmap %s gerado para %s. Revisão humana pendente; nada foi ativado.",
            result["id"],
            result["reference_year"],
        )
        return result

    def diff(self, version_id: int) -> dict:
        draft = self._require(version_id)
        draft_rows = self.versions.topics_for(draft.id)
        base, base_low, active_id = self._diff_base(draft.id)
        names = {topic.id: topic.name for topic in self.topics.list_ordered()}
        moved, new_low = _diff_changes(draft_rows, base, base_low, names)
        coverage = draft.coverage_map()
        minimum = float(current_app.config["ROADMAP_MIN_COVERAGE"])
        return {
            "draft_id": draft.id,
            "active_id": active_id,
            "moved": moved,
            "new_low_incidence": new_low,
            "coverage": {str(year): value for year, value in coverage.items()},
            "below_minimum": _below_minimum(coverage, minimum),
            "minimum_coverage": minimum,
        }

    def _diff_base(self, draft_id):
        active = self.versions.get_active()
        if active and active.id != draft_id:
            base_rows = self.versions.topics_for(active.id)
            base = {row.topic_id: row.position for row in base_rows}
            base_low = {row.topic_id: bool(row.low_incidence) for row in base_rows}
            return base, base_low, active.id
        ordered = self.topics.list_ordered()
        base = {topic.id: index for index, topic in enumerate(ordered, start=1)}
        base_low = {topic.id: False for topic in ordered}
        return base, base_low, None

    def activate(self, version_id: int, *, allow_low_coverage: bool = False) -> dict:
        draft = self._require(version_id)
        if draft.status != "draft":
            raise RoadmapDataError("Só um rascunho pode ser ativado.")
        coverage = draft.coverage_map()
        minimum = float(current_app.config["ROADMAP_MIN_COVERAGE"])
        if any(value < minimum for value in coverage.values()) and not allow_low_coverage:
            raise RoadmapDataError(
                "Cobertura abaixo do mínimo. Use --allow-low-coverage para ativar mesmo assim."
            )
        previous = self.versions.get_active()
        if previous and previous.id != draft.id:
            previous.status = "archived"
            self.versions.flush()
        draft.status = "active"
        draft.activated_at = self.clock.now_utc()
        self._notify(draft)
        self.versions.commit()
        return self._version_payload(draft)

    def list_versions(self) -> list[dict]:
        return [self._version_payload(version) for version in self.versions.list_versions()]

    def active_summary(self) -> dict | None:
        active = self.versions.get_active()
        if active is None:
            return None
        return active.to_summary()

    def active_incidence(self) -> dict[int, dict] | None:
        active = self.versions.get_active()
        if active is None:
            return None
        overlay = {}
        for row in self.versions.topics_for(active.id):
            overlay[row.topic_id] = {
                "position": row.position,
                "incidence_weight": row.incidence_weight,
                "incidence_count": row.incidence_count,
                "low_incidence": bool(row.low_incidence),
                "rank_reason": row.rank_reason,
            }
        return overlay

    def unseen_notices(self, user_id: int) -> list[dict]:
        return [notice.to_dict() for notice in self.versions.unseen_notices(user_id)]

    def dismiss_notice(self, user_id: int, notice_id: int) -> dict | None:
        notice = self.versions.get_notice(notice_id)
        if notice is None or notice.user_id != user_id:
            return None
        if notice.seen_at is None:
            notice.seen_at = self.clock.now_utc()
            self.versions.commit()
        return notice.to_dict()

    def _notify(self, version: RoadmapVersion) -> None:
        editions = version.edition_list()
        message = (
            f"Seu roadmap foi atualizado com as provas de {edition_span(editions)}. "
            "Seu progresso foi mantido."
        )
        payload = dump_json({"message": message, "version_id": version.id, "editions": editions})
        now = self.clock.now_utc()
        for user_id in self.versions.user_ids_with_progress():
            current = self.versions.unseen_notice(user_id, NOTICE_KIND)
            if current:
                current.payload = payload
                current.created_at = now
                continue
            self.versions.add_notice(
                UserNotice(
                    user_id=user_id,
                    kind=NOTICE_KIND,
                    payload=payload,
                    created_at=now,
                )
            )

    def _skills(self, catalog, slug_index) -> tuple[list[tuple[str, str]], dict]:
        if catalog.skill_map is None:
            return [], {}
        color = str(current_app.config["INEP_REFERENCE_COLOR"])
        seen = {}
        for row in self.inep.list_reference_items(catalog.editions, color):
            if row.abandoned:
                continue
            skill = (row.skill_code or "").strip().upper()
            if not skill:
                continue
            seen[(row.year, row.area, row.position)] = (row.area.strip().upper(), skill)
        mapping = defaultdict(list)
        for area, skill, slug in catalog.skill_map:
            topic_id = slug_index[slug].id
            if topic_id not in mapping[(area, skill)]:
                mapping[(area, skill)].append(topic_id)
        return list(seen.values()), mapping

    def _folder(self, data_dir: str | None) -> Path:
        if data_dir:
            return Path(data_dir)
        return Path(current_app.config["ROADMAP_DATA_DIR"])

    def _require(self, version_id: int) -> RoadmapVersion:
        version = self.versions.get_by_id(version_id)
        if version is None:
            raise RoadmapDataError(f"Versão {version_id} não existe.")
        return version

    def _version_payload(self, version: RoadmapVersion) -> dict:
        return {
            "id": version.id,
            "reference_year": version.reference_year,
            "editions": version.edition_list(),
            "edital": version.edital,
            "matrix_reference": version.matrix_reference,
            "status": version.status,
            "coverage": {str(year): value for year, value in version.coverage_map().items()},
            "generated_at": version.generated_at.isoformat() if version.generated_at else None,
            "activated_at": version.activated_at.isoformat() if version.activated_at else None,
        }

def _diff_changes(draft_rows, base, base_low, names):
    moved = []
    new_low = []
    for row in draft_rows:
        shift = _moved_topic(row, base, names)
        if shift:
            moved.append(shift)
        low = _new_low_topic(row, base_low, names)
        if low:
            new_low.append(low)
    return moved, new_low

def _moved_topic(row, base, names):
    origin = base.get(row.topic_id)
    if origin is None or abs(row.position - origin) < 5:
        return None
    return {
        "topic_id": row.topic_id,
        "name": names.get(row.topic_id, ""),
        "from": origin,
        "to": row.position,
        "delta": row.position - origin,
    }

def _new_low_topic(row, base_low, names):
    if not row.low_incidence:
        return None
    if base_low.get(row.topic_id, False):
        return None
    return {"topic_id": row.topic_id, "name": names.get(row.topic_id, "")}

def _below_minimum(coverage, minimum) -> bool:
    for value in coverage.values():
        if value < minimum:
            return True
    return False
