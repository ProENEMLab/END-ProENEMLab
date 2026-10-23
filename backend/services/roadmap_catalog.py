from __future__ import annotations

import csv
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

class RoadmapDataError(Exception):
    pass

@dataclass
class RoadmapCatalog:

    reference_year: int
    editions: list[int]
    application: str
    edital: str
    matrix_reference: str
    notes: str
    prerequisites: list[tuple[str, str]]
    skill_map: list[tuple[str, str, str]] | None

def topic_slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower().replace("º", "o").replace("°", "o")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")

def load_catalog(folder: Path) -> RoadmapCatalog:
    editions_path = folder / "exam_editions.yaml"
    prerequisites_path = folder / "topic_prerequisites.csv"
    if not editions_path.is_file():
        raise RoadmapDataError(f"Arquivo obrigatório ausente: {editions_path.name}.")
    if not prerequisites_path.is_file():
        raise RoadmapDataError(f"Arquivo obrigatório ausente: {prerequisites_path.name}.")
    raw = _parse_yaml(editions_path.read_text(encoding="utf-8"))
    skill_path = folder / "skill_topic_map.csv"
    skill_map = _read_skills(skill_path) if skill_path.is_file() else None
    return RoadmapCatalog(
        reference_year=_required_int(raw, "reference_year"),
        editions=_required_editions(raw),
        application=_required_text(raw, "application"),
        edital=_required_text(raw, "edital"),
        matrix_reference=_required_text(raw, "matrix_reference"),
        notes=_optional_text(raw, "notes"),
        prerequisites=_read_prerequisites(prerequisites_path),
        skill_map=skill_map,
    )

def index_topics(topics) -> dict[str, object]:
    found: dict[str, object] = {}
    for topic in topics:
        slug = topic_slug(topic.name)
        if not slug:
            raise RoadmapDataError(f"O tópico '{topic.name}' não gera um slug.")
        if slug in found:
            raise RoadmapDataError(f"Dois tópicos geram o slug '{slug}'.")
        found[slug] = topic
    return found

def validate_catalog(catalog: RoadmapCatalog, slug_index: dict, reference_year: int) -> None:
    if catalog.reference_year != reference_year:
        raise RoadmapDataError(
            "exam_editions.yaml: o ano de referência é "
            f"{catalog.reference_year}, não {reference_year}."
        )
    distinct = list(dict.fromkeys(catalog.editions))
    if len(distinct) != 5 or len(catalog.editions) != 5:
        raise RoadmapDataError(
            "exam_editions.yaml: são necessárias 5 edições distintas, "
            f"encontradas {len(set(catalog.editions))}."
        )
    if catalog.editions != sorted(catalog.editions):
        raise RoadmapDataError("exam_editions.yaml: as edições devem estar em ordem crescente.")
    if catalog.application != "regular":
        raise RoadmapDataError(
            "exam_editions.yaml: application tem que ser regular (exclui PPL e reaplicação)."
        )
    _known_slugs(catalog.prerequisites, slug_index, "topic_prerequisites.csv")
    _assert_acyclic(catalog.prerequisites)
    if catalog.skill_map is not None:
        _known_slugs(
            [(slug, slug) for _area, _skill, slug in catalog.skill_map],
            slug_index,
            "skill_topic_map.csv",
        )

def _known_slugs(pairs: list[tuple[str, str]], slug_index: dict, filename: str) -> None:
    for left, right in pairs:
        for slug in (left, right):
            if slug not in slug_index:
                raise RoadmapDataError(f"{filename}: slug inexistente '{slug}'.")

def _assert_acyclic(edges: list[tuple[str, str]]) -> None:
    graph: dict[str, list[str]] = defaultdict(list)
    nodes: set[str] = set()
    for topic, prerequisite in edges:
        if topic == prerequisite:
            raise RoadmapDataError(
                f"topic_prerequisites.csv: ciclo de pré-requisitos envolvendo '{topic}'."
            )
        graph[prerequisite].append(topic)
        nodes.add(topic)
        nodes.add(prerequisite)
    color: dict[str, int] = {}

    def visit(node: str, stack: list[str]) -> None:
        color[node] = 1
        stack.append(node)
        for nxt in graph[node]:
            if color.get(nxt) == 1:
                cycle = stack[stack.index(nxt) :] + [nxt]
                raise RoadmapDataError(
                    "topic_prerequisites.csv: ciclo de pré-requisitos envolvendo "
                    + " → ".join(cycle)
                    + "."
                )
            if color.get(nxt) != 2:
                visit(nxt, stack)
        stack.pop()
        color[node] = 2

    for node in sorted(nodes):
        if color.get(node) != 2:
            visit(node, [])

def _parse_yaml(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = _strip_comment(raw_line).strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data

def _strip_comment(line: str) -> str:
    quoted = False
    for index, char in enumerate(line):
        if char == '"':
            quoted = not quoted
        elif char == "#" and not quoted:
            return line[:index]
    return line

def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value

def _required_text(raw: dict[str, str], key: str) -> str:
    if key not in raw or not _unquote(raw[key]).strip():
        raise RoadmapDataError(f"exam_editions.yaml: campo obrigatório ausente '{key}'.")
    return _unquote(raw[key]).strip()

def _optional_text(raw: dict[str, str], key: str) -> str:
    if key not in raw:
        return ""
    return _unquote(raw[key]).strip()

def _required_int(raw: dict[str, str], key: str) -> int:
    text = _required_text(raw, key)
    if not text.isdigit():
        raise RoadmapDataError(f"exam_editions.yaml: '{key}' tem que ser um ano inteiro.")
    return int(text)

def _required_editions(raw: dict[str, str]) -> list[int]:
    text = _required_text(raw, "editions")
    if not (text.startswith("[") and text.endswith("]")):
        raise RoadmapDataError("exam_editions.yaml: editions tem que ser uma lista [ano, ...].")
    parts = [part.strip() for part in text[1:-1].split(",") if part.strip()]
    editions = []
    for part in parts:
        if not part.isdigit():
            raise RoadmapDataError(f"exam_editions.yaml: edição inválida '{part}'.")
        editions.append(int(part))
    return editions

def _read_prerequisites(path: Path) -> list[tuple[str, str]]:
    rows = _read_csv(path, ("topic_slug", "prerequisite_slug"))
    edges = []
    seen = set()
    for row in rows:
        topic = row["topic_slug"].strip()
        prerequisite = row["prerequisite_slug"].strip()
        if not topic or not prerequisite:
            raise RoadmapDataError("topic_prerequisites.csv: slug em branco.")
        key = (topic, prerequisite)
        if key in seen:
            continue
        seen.add(key)
        edges.append(key)
    return edges

def _read_skills(path: Path) -> list[tuple[str, str, str]]:
    rows = _read_csv(path, ("area", "skill_code", "topic_slug"))
    mapped = []
    for row in rows:
        area = row["area"].strip().upper()
        skill = row["skill_code"].strip().upper()
        slug = row["topic_slug"].strip()
        if not area or not skill or not slug:
            raise RoadmapDataError("skill_topic_map.csv: área, habilidade ou slug em branco.")
        mapped.append((area, skill, slug))
    return mapped

def _read_csv(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(path, reader.fieldnames or [], columns)
        rows = []
        for row in reader:
            if _blank_csv(row):
                continue
            rows.append(_csv_row(row, columns))
        return rows

def _require_columns(path, header, columns):
    missing = [column for column in columns if column not in header]
    if missing:
        raise RoadmapDataError(
            f"{path.name}: colunas obrigatórias ausentes: {', '.join(missing)}."
        )

def _blank_csv(row) -> bool:
    if not row:
        return True
    for value in row.values():
        text = value or ""
        if text.strip():
            return False
    return True

def _csv_row(row, columns):
    cleaned = {}
    for key in columns:
        cleaned[key] = row.get(key) or ""
    return cleaned
