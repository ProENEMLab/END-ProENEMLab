import csv
import io
from pathlib import Path

from flask import current_app

from models.inep import InepItemParam
from models.question import Question
from repositories.inep_item_repository import InepItemRepository
from repositories.question_repository import QuestionRepository
from services.difficulty_service import DifficultyService
from services.subject_names import SUBJECT_AREA

AREAS = {"LC", "CH", "CN", "MT"}

class InepImportService:

    def __init__(
        self,
        inep_repository: InepItemRepository,
        question_repository: QuestionRepository,
        difficulty_service: DifficultyService,
    ) -> None:
        self.inep = inep_repository
        self.questions = question_repository
        self.difficulty = difficulty_service

    def import_items(self, year: int, file_path: str | None = None) -> dict:
        path = Path(file_path or self._default_path(year))
        summary = {"read": 0, "inserted": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        for raw in _read_rows(path):
            summary["read"] += 1
            parsed = _parse_row(raw, year)
            if parsed is None:
                summary["skipped"] += 1
                continue
            current = self.inep.find_slot(year, parsed["booklet_code"], parsed["position"])
            if current is None:
                self.inep.add(InepItemParam(**parsed))
                summary["inserted"] += 1
                continue
            if _same_item(current, parsed):
                summary["unchanged"] += 1
                continue
            for key, value in parsed.items():
                setattr(current, key, value)
            summary["updated"] += 1
        self.inep.commit()
        return summary

    def link_questions(self, year: int | None = None) -> dict:
        color = str(current_app.config["INEP_REFERENCE_COLOR"]).upper()
        summary = {
            "read": 0,
            "linked": 0,
            "unmatched": 0,
            "answer_mismatch": 0,
            "ambiguous": 0,
        }
        for question in self.questions.list_for_linking(year):
            summary["read"] += 1
            outcome = self._link_one(question, color)
            summary[outcome] += 1
        self.questions.commit()
        return summary

    def recompute(self) -> dict:
        return self.difficulty.recompute()

    def _link_one(self, question: Question, color: str) -> str:
        area = SUBJECT_AREA.get(question.subject)
        if question.enem_index is None or area is None:
            question.inep_item_code = None
            return "unmatched"
        matches = self.inep.reference_matches(question.year, area, question.enem_index, color)
        if len(matches) > 1:
            question.inep_item_code = None
            return "ambiguous"
        if not matches:
            question.inep_item_code = None
            return "unmatched"
        item = matches[0]
        if (item.answer_key or "").strip().upper() != (
            question.correct_option or ""
        ).strip().upper():
            question.inep_item_code = None
            return "answer_mismatch"
        question.inep_item_code = item.item_code
        return "linked"

    def _default_path(self, year: int) -> str:
        folder = current_app.config["INEP_ITEMS_DIR"]
        return str(Path(folder) / f"ITENS_PROVA_{year}.csv")

def _read_rows(path: Path) -> list[dict]:
    text = _decode(path.read_bytes())
    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    rows = []
    for row in reader:
        rows.append({(key or "").strip().upper(): value for key, value in row.items()})
    return rows

def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")

def _parse_row(raw: dict, year: int) -> dict | None:
    area = _cell(raw, "SG_AREA").upper()
    booklet = _cell(raw, "CO_PROVA")
    position = _int(raw.get("CO_POSICAO"))
    item_code = _cell(raw, "CO_ITEM")
    if not _row_usable(area, booklet, position, item_code):
        return None
    return {
        "year": year,
        "area": area,
        "item_code": item_code,
        "position": position,
        "booklet_code": booklet,
        "booklet_color": _optional_cell(raw, "TX_COR", upper=True),
        "answer_key": _optional_cell(raw, "TX_GABARITO", upper=True),
        "skill_code": _optional_cell(raw, "CO_HABILIDADE"),
        "param_a": _float(raw.get("NU_PARAM_A")),
        "param_b": _float(raw.get("NU_PARAM_B")),
        "param_c": _float(raw.get("NU_PARAM_C")),
        "abandoned": _abandoned(raw.get("IN_ITEM_ABAN")),
    }

def _cell(raw, key) -> str:
    value = raw.get(key)
    if value is None:
        return ""
    return str(value).strip()

def _optional_cell(raw, key, upper=False):
    text = _cell(raw, key)
    if upper:
        text = text.upper()
    if not text:
        return None
    return text

def _row_usable(area, booklet, position, item_code) -> bool:
    if area not in AREAS:
        return False
    if not booklet:
        return False
    if position is None:
        return False
    if not item_code:
        return False
    return True

def _same_item(current: InepItemParam, parsed: dict) -> bool:
    for key, value in parsed.items():
        current_value = getattr(current, key)
        if key.startswith("param_") or key in {"param_a", "param_b", "param_c"}:
            if not _same_float(current_value, value):
                return False
            continue
        if key == "abandoned":
            if bool(current_value) != bool(value):
                return False
            continue
        if current_value != value:
            return False
    return True

def _same_float(left, right) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return float(left) == float(right)

def _int(raw) -> int | None:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return None

def _float(raw) -> float | None:
    text = (raw or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None

def _abandoned(raw) -> bool:
    return (raw or "").strip().upper() in {"1", "S", "SIM", "TRUE"}
