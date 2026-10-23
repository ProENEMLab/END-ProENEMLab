from __future__ import annotations

from collections import defaultdict

from services.roadmap_catalog import RoadmapDataError

FOREIGN_LANGUAGES = {"ingles", "inglês", "english", "espanhol", "spanish"}

def edition_span(editions: list[int]) -> str:
    if not editions:
        return ""
    if editions[0] == editions[-1]:
        return str(editions[0])
    return f"{editions[0]}–{editions[-1]}"

def format_percent(weight: float) -> str:
    value = round(weight * 100, 1)
    return f"{value:.1f}".replace(".", ",") + "%"

def questions_to_slots(
    questions, abandoned: set[tuple[int, str]]
) -> tuple[list[dict], dict[int, int]]:
    grouped, order = _group_questions(questions, abandoned)
    return _slots_from(grouped, order)

def _group_questions(questions, abandoned):
    grouped: dict[tuple, list] = {}
    order: list[tuple] = []
    for question in questions:
        if _skip_slot(question, abandoned):
            continue
        key = _slot_key(question)
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(question)
    return grouped, order

def _skip_slot(question, abandoned) -> bool:
    if _excluded_application(question):
        return True
    code = (question.inep_item_code or "").strip()
    if code and (question.year, code) in abandoned:
        return True
    return False

def _slots_from(grouped, order):
    slots = []
    per_year: dict[int, int] = defaultdict(int)
    for key in order:
        chosen = _pick_representative(grouped[key])
        topic_ids = [chosen.topic_id] if chosen.topic_id else []
        slots.append({"year": chosen.year, "topic_ids": list(topic_ids)})
        per_year[chosen.year] += 1
    return slots, dict(per_year)

def compute_incidence(
    slots: list[dict],
    topic_ids: list[int],
    skill_items: list[tuple[str, str]],
    skill_map: dict[tuple[str, str], list[int]],
) -> dict[int, tuple[int, float]]:
    known = set(topic_ids)
    shares, touch = _question_shares(slots, known)
    covered = {topic_id for topic_id, count in touch.items() if count}
    skill_share, skill_touch = _skill_shares(skill_items, skill_map, known, covered)
    return _measured(topic_ids, shares, touch, skill_share, skill_touch, len(slots))

def _question_shares(slots, known):
    shares: dict[int, float] = defaultdict(float)
    touch: dict[int, int] = defaultdict(int)
    for slot in slots:
        _add_share(_kept_ids(slot["topic_ids"], known, set()), shares, touch)
    return shares, touch

def _skill_shares(skill_items, skill_map, known, covered):
    shares: dict[int, float] = defaultdict(float)
    touch: dict[int, int] = defaultdict(int)
    for area, skill in skill_items:
        raw = skill_map.get((area, skill), [])
        _add_share(_kept_ids(raw, known, covered), shares, touch)
    return shares, touch

def _kept_ids(raw_ids, known, skip):
    ids = []
    for topic_id in raw_ids:
        if topic_id not in known:
            continue
        if topic_id in skip or topic_id in ids:
            continue
        ids.append(topic_id)
    return ids

def _add_share(ids, shares, touch):
    if not ids:
        return
    part = 1 / len(ids)
    for topic_id in ids:
        shares[topic_id] += part
        touch[topic_id] += 1

def _measured(topic_ids, shares, touch, skill_share, skill_touch, total):
    measured = {}
    for topic_id in topic_ids:
        measured[topic_id] = _topic_weight(
            topic_id, shares, touch, skill_share, skill_touch, total
        )
    return measured

def _topic_weight(topic_id, shares, touch, skill_share, skill_touch, total):
    if touch[topic_id]:
        count = touch[topic_id]
        raw = shares[topic_id]
    else:
        count = skill_touch[topic_id]
        raw = skill_share[topic_id]
    weight = raw / total if total else 0.0
    return count, round(weight, 6)

def coverage_by_edition(
    per_year: dict[int, int], editions: list[int], expected: int
) -> dict[int, float]:
    if expected <= 0:
        raise RoadmapDataError("ENEM_OBJECTIVE_QUESTIONS_PER_EDITION tem que ser positivo.")
    return {year: round(per_year.get(year, 0) / expected, 4) for year in editions}

def rank_topics(
    topics, weights: dict[int, float], prerequisites: list[tuple[int, int]], editions: list[int]
) -> list[dict]:
    by_id = {topic.id: topic for topic in topics}
    dependents, indegree = _links(topics, prerequisites, by_id)
    placed = _place_topics(by_id, dependents, indegree, weights)
    return _ranked_rows(placed, by_id, weights, dependents, editions)

def _links(topics, prerequisites, by_id):
    dependents: dict[int, list[int]] = defaultdict(list)
    indegree = {topic.id: 0 for topic in topics}
    for topic_id, prerequisite_id in prerequisites:
        _link(topic_id, prerequisite_id, by_id, dependents, indegree)
    return dependents, indegree

def _link(topic_id, prerequisite_id, by_id, dependents, indegree):
    if topic_id not in by_id or prerequisite_id not in by_id:
        raise RoadmapDataError("Pré-requisito aponta para um tópico que não está no banco.")
    dependents[prerequisite_id].append(topic_id)
    indegree[topic_id] += 1

def _place_topics(by_id, dependents, indegree, weights):
    remaining = set(indegree)
    placed: list[int] = []
    while remaining:
        chosen = _next_topic(remaining, indegree, dependents, weights, by_id)
        placed.append(chosen)
        remaining.remove(chosen)
        for child in dependents[chosen]:
            indegree[child] -= 1
    return placed

def _next_topic(remaining, indegree, dependents, weights, by_id):
    available = [topic_id for topic_id in remaining if indegree[topic_id] == 0]
    if not available:
        raise RoadmapDataError("topic_prerequisites.csv: ciclo de pré-requisitos.")
    pool = _blocking(available, dependents, remaining, weights) or available
    pool.sort(
        key=lambda topic_id: (-weights.get(topic_id, 0), by_id[topic_id].order_index, topic_id)
    )
    return pool[0]

def _blocking(available, dependents, remaining, weights):
    blocking = []
    for topic_id in available:
        if weights.get(topic_id, 0) > 0 or _blocks(topic_id, dependents, remaining):
            blocking.append(topic_id)
    return blocking

def _ranked_rows(placed, by_id, weights, dependents, editions):
    span = edition_span(editions)
    labels = _terciles(weights)
    rows = []
    for position, topic_id in enumerate(placed, start=1):
        rows.append(_rank_row(position, topic_id, by_id, weights, labels, dependents, span))
    return rows

def _rank_row(position, topic_id, by_id, weights, labels, dependents, span):
    weight = weights.get(topic_id, 0)
    return {
        "topic_id": topic_id,
        "position": position,
        "low_incidence": weight <= 0,
        "rank_reason": _reason(topic_id, weight, labels, dependents, by_id, weights, span),
    }

def _blocks(topic_id: int, dependents: dict[int, list[int]], remaining: set[int]) -> bool:
    return any(child in remaining and child != topic_id for child in dependents[topic_id])

def _terciles(weights: dict[int, float]) -> dict[int, str]:
    positive = sorted(weight for weight in weights.values() if weight > 0)
    return {topic_id: _band(weight, positive) for topic_id, weight in weights.items()}

def _band(weight, positive) -> str:
    if weight <= 0 or not positive:
        return "zero"
    rank = sum(1 for value in positive if value <= weight) / len(positive)
    if rank > 2 / 3:
        return "alta"
    if rank > 1 / 3:
        return "media"
    return "baixa"

def _reason(topic_id, weight, labels, dependents, by_id, weights, span: str) -> str:
    parent = _prerequisite_reason(topic_id, weight, dependents, by_id, weights)
    if parent:
        return parent
    if weight <= 0:
        return f"Incidência baixa nas provas de {span}. O tópico permanece no roadmap."
    return _incidence_reason(topic_id, weight, labels, span)

def _prerequisite_reason(topic_id, weight, dependents, by_id, weights) -> str:
    higher = []
    for child in dependents[topic_id]:
        if child not in by_id:
            continue
        if weights.get(child, 0) > weight:
            higher.append(child)
    if not higher:
        return ""
    best = min(higher, key=lambda child: (-weights.get(child, 0), by_id[child].name))
    return f"Pré-requisito de {by_id[best].name}"

def _incidence_reason(topic_id, weight, labels, span: str) -> str:
    percent = format_percent(weight)
    label = labels.get(topic_id)
    if label == "alta":
        return f"Alta incidência: {percent} das questões de {span}"
    if label == "media":
        return f"Incidência média: {percent} das questões de {span}"
    return f"Incidência de {percent} das questões de {span}"

def _excluded_application(question) -> bool:
    title = f"{getattr(question, 'enem_title', '') or ''}".lower()
    return "ppl" in title or "reaplic" in title

def _slot_key(question) -> tuple:
    language = (question.language or "").strip().lower()
    if language in FOREIGN_LANGUAGES and question.enem_index is not None:
        return (question.year, "lang", question.enem_index)
    return (question.year, "item", question.id)

def _pick_representative(group: list):
    def sort_key(question):
        language = (question.language or "").strip().lower()
        prefer = 0 if language in {"ingles", "inglês", "english"} else 1
        return (prefer, question.id)

    return sorted(group, key=sort_key)[0]
