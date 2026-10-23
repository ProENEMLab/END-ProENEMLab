from datetime import datetime, timezone

from flask import current_app

from models.inep import InepDifficultyCutoff, InepItemParam
from models.question import Question
from repositories.attempt_repository import AttemptRepository
from repositories.inep_item_repository import InepItemRepository
from repositories.question_repository import QuestionRepository
from services.subject_names import AREA_LABEL, SUBJECT_AREA

LEVELS = ("easy", "medium", "hard")

def band_for_rate(rate: float, easy_min: float, medium_min: float) -> str:
    if rate >= easy_min:
        return "easy"
    if rate >= medium_min:
        return "medium"
    return "hard"

def split_terciles(items: list[InepItemParam]) -> tuple[dict[tuple, str], dict[str, dict]]:
    by_area: dict[str, list[InepItemParam]] = {}
    for item in items:
        if item.abandoned or item.param_b is None:
            continue
        by_area.setdefault(item.area, []).append(item)

    levels: dict[tuple, str] = {}
    cutoffs: dict[str, dict] = {}
    for area, rows in by_area.items():
        ordered = sorted(rows, key=lambda row: (row.param_b, row.year, row.item_code))
        total = len(ordered)
        easy_cut = total // 3
        medium_cut = (2 * total) // 3
        buckets = {level: [] for level in LEVELS}
        for index, row in enumerate(ordered):
            if index < easy_cut:
                level = "easy"
            elif index < medium_cut:
                level = "medium"
            else:
                level = "hard"
            levels[(row.area, row.year, row.item_code)] = level
            buckets[level].append(row)
        label = AREA_LABEL.get(area, area)
        cutoffs[area] = {
            "easy_max": _max_b(buckets["easy"]),
            "medium_max": _max_b(buckets["medium"]),
            "easy_count": len(buckets["easy"]),
            "medium_count": len(buckets["medium"]),
            "hard_count": len(buckets["hard"]),
            "note": f"Difícil = entre os 33% mais difíceis de {label}.",
        }
    return levels, cutoffs

class DifficultyService:

    def __init__(
        self,
        question_repository: QuestionRepository,
        inep_repository: InepItemRepository,
        attempt_repository: AttemptRepository,
    ) -> None:
        self.questions = question_repository
        self.inep = inep_repository
        self.attempts = attempt_repository

    def recompute(self) -> dict:
        representatives = _representatives(self.inep.list_all(), _reference_color())
        levels, cutoffs = split_terciles(representatives)
        self._store_cutoffs(cutoffs)
        stats = self.attempts.first_attempt_stats()
        now = datetime.now(timezone.utc)
        summary = {
            "questions": 0,
            "by_source": {"inep_tri": 0, "platform": 0, "unclassified": 0},
            "by_level": {"easy": 0, "medium": 0, "hard": 0, "unclassified": 0},
        }
        lookup = _lookup(representatives)
        for question in self.questions.list_all():
            summary["questions"] += 1
            source, level = self._classify(question, lookup, levels, stats)
            self._assign(question, level, source, _value_for(question, lookup, source, stats), now)
            source_key = source or "unclassified"
            level_key = level or "unclassified"
            summary["by_source"][source_key] = summary["by_source"].get(source_key, 0) + 1
            summary["by_level"][level_key] = summary["by_level"].get(level_key, 0) + 1
        self.questions.commit()
        return summary

    def _classify(self, question, lookup, levels, stats) -> tuple[str | None, str | None]:
        item = _item_for(question, lookup)
        if item is not None and item.abandoned:
            return None, None
        if item is not None and item.param_b is not None:
            level = levels.get((item.area, item.year, item.item_code))
            if level:
                return "inep_tri", level
        if question.difficulty_source == "inep_tri" and question.difficulty in LEVELS:
            return "inep_tri", question.difficulty
        users, correct = stats.get(question.id, (0, 0))
        minimum = int(current_app.config["DIFFICULTY_MIN_PLATFORM_ATTEMPTS"])
        if users < minimum:
            return None, None
        rate = correct / users
        return "platform", band_for_rate(rate, self._easy(), self._medium())

    def _assign(self, question, level, source, value, now) -> None:
        if (
            question.difficulty == level
            and question.difficulty_source == source
            and _same_number(question.difficulty_value, value)
        ):
            return
        question.difficulty = level
        question.difficulty_source = source
        question.difficulty_value = value
        question.difficulty_updated_at = now

    def _store_cutoffs(self, cutoffs: dict[str, dict]) -> None:
        now = datetime.now(timezone.utc)
        existing = {row.area: row for row in self.inep.list_cutoffs()}
        seen = set()
        for area, payload in cutoffs.items():
            seen.add(area)
            current = existing.get(area)
            if current and _cutoff_same(current, payload):
                continue
            if current is None:
                current = InepDifficultyCutoff(area=area)
                self.inep.add(current)
            current.easy_max = payload["easy_max"]
            current.medium_max = payload["medium_max"]
            current.easy_count = payload["easy_count"]
            current.medium_count = payload["medium_count"]
            current.hard_count = payload["hard_count"]
            current.note = payload["note"]
            current.updated_at = now
        for area, row in existing.items():
            if area not in seen:
                self.inep.delete(row)

    def _easy(self) -> float:
        return float(current_app.config["DIFFICULTY_EASY_MIN_RATE"])

    def _medium(self) -> float:
        return float(current_app.config["DIFFICULTY_MEDIUM_MIN_RATE"])

def _value_for(question, lookup, source, stats) -> float | None:
    if source == "inep_tri":
        item = _item_for(question, lookup)
        if item is not None and item.param_b is not None:
            return float(item.param_b)
        return question.difficulty_value
    if source == "platform":
        users, correct = stats.get(question.id, (0, 0))
        if not users:
            return None
        return correct / users
    return None

def _representatives(rows: list[InepItemParam], color: str) -> list[InepItemParam]:
    chosen: dict[tuple, InepItemParam] = {}
    for row in rows:
        key = (row.area, row.year, row.item_code)
        current = chosen.get(key)
        if current is None or _prefers(row, current, color):
            chosen[key] = row
    return list(chosen.values())

def _prefers(row: InepItemParam, current: InepItemParam, color: str) -> bool:
    row_ref = (row.booklet_color or "").upper() == color
    current_ref = (current.booklet_color or "").upper() == color
    return row_ref and not current_ref

def _lookup(rows: list[InepItemParam]) -> dict[tuple, list[InepItemParam]]:
    grouped: dict[tuple, list[InepItemParam]] = {}
    for row in rows:
        grouped.setdefault((row.year, row.item_code), []).append(row)
    return grouped

def _item_for(question: Question, lookup) -> InepItemParam | None:
    if not question.inep_item_code:
        return None
    candidates = lookup.get((question.year, question.inep_item_code), [])
    area = SUBJECT_AREA.get(question.subject)
    for row in candidates:
        if row.area == area:
            return row
    return candidates[0] if candidates else None

def _reference_color() -> str:
    return str(current_app.config["INEP_REFERENCE_COLOR"]).upper()

def _max_b(rows: list[InepItemParam]) -> float | None:
    if not rows:
        return None
    return max(row.param_b for row in rows)

def _same_number(left, right) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return float(left) == float(right)

def _cutoff_same(row: InepDifficultyCutoff, payload: dict) -> bool:
    return (
        _same_number(row.easy_max, payload["easy_max"])
        and _same_number(row.medium_max, payload["medium_max"])
        and row.easy_count == payload["easy_count"]
        and row.medium_count == payload["medium_count"]
        and row.hard_count == payload["hard_count"]
        and row.note == payload["note"]
    )
