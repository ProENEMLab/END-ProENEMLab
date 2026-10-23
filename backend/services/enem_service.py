from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from flask import current_app

from services.exceptions import EnemApiError
from models.question import (
    DEFAULT_ENEM_EXPLANATION,
    SOURCE_ATTRIBUTION,
    Question,
    QuestionOption,
)
from repositories.option_repository import OptionRepository
from repositories.question_repository import QuestionRepository
from services.subject_names import DISCIPLINE_TO_SUBJECT, normalize_subject

logger = logging.getLogger(__name__)

FetchFn = Callable[[str], Any]
LANGUAGE_PASSES = (None, "ingles", "espanhol")
PAGE_SIZE = 50

__all__ = ["EnemApiError", "EnemService", "normalize_subject"]

def fetch_json(url: str, timeout: int = 25, retries: int = 4) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            return _read_json(url, timeout)
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if err.code != 429:
                raise EnemApiError(f"enem-api HTTP {err.code} em {url}", err.code)
            last_error = err
            time.sleep(_retry_wait(err, attempt))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            last_error = err
            time.sleep(1.5 * (attempt + 1))
    raise EnemApiError(f"Falha ao consultar enem-api: {last_error}")

def list_remote_exams(fetch: FetchFn | None = None) -> list[dict]:
    fetch = fetch or fetch_json
    payload = fetch(f"{_api_base()}/exams")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("exams") or payload.get("items") or []
    return []

class EnemService:

    def __init__(
        self,
        question_repository: QuestionRepository,
        option_repository: OptionRepository,
    ) -> None:
        self.questions = question_repository
        self.options = option_repository

    def sync_exams(
        self,
        year: int | None = None,
        all_years: bool = False,
        fetch: FetchFn | None = None,
    ) -> dict:
        fetch = fetch or fetch_json
        targets = self._target_years(year, all_years, fetch)
        results = [self.sync_exam(item, fetch=fetch) for item in targets]
        return {
            "attribution": SOURCE_ATTRIBUTION,
            "years": targets,
            "results": results,
        }

    def sync_exam(self, year: int, fetch: FetchFn | None = None) -> dict:
        fetch = fetch or fetch_json
        created, updated, seen = self._sync_year(year, fetch)
        self.questions.commit()
        return {"year": year, "seen": seen, "created": created, "updated": updated}

    def _target_years(self, year: int | None, all_years: bool, fetch: FetchFn) -> list[int]:
        exams = list_remote_exams(fetch)
        years = sorted({int(exam["year"]) for exam in exams if exam.get("year")}, reverse=True)
        if year:
            return [year]
        if all_years:
            return years
        return years[:3] or ([year] if year else [])

    def _sync_year(self, year: int, fetch: FetchFn) -> tuple[int, int, int]:
        created = updated = seen = 0
        for language in LANGUAGE_PASSES:
            page_created, page_updated, page_seen = self._sync_language(year, language, fetch)
            created += page_created
            updated += page_updated
            seen += page_seen
            if language is None and seen == 0:
                continue
        return created, updated, seen

    def _sync_language(
        self, year: int, language: str | None, fetch: FetchFn
    ) -> tuple[int, int, int]:
        created = updated = seen = 0
        offset = 0
        while True:
            items = self._fetch_page(year, language, offset, fetch)
            if not items:
                break
            for item in items:
                was_new = self._store_item(item, year, language)
                seen += 1
                created += int(was_new)
                updated += int(not was_new)
            if len(items) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
            time.sleep(0.12)
        return created, updated, seen

    def _fetch_page(
        self, year: int, language: str | None, offset: int, fetch: FetchFn
    ) -> list[dict]:
        params = {"limit": PAGE_SIZE, "offset": offset}
        if language:
            params["language"] = language
        query = urllib.parse.urlencode(params)
        payload = fetch(f"{_api_base()}/exams/{year}/questions?{query}")
        return _extract_questions(payload)

    def _store_item(self, item: dict, year: int, language: str | None) -> bool:
        item.setdefault("year", year)
        if language and not item.get("language"):
            item["language"] = language
        return self._upsert_question(item)

    def _upsert_question(self, item: dict) -> bool:
        year = item.get("year")
        index = item.get("index")
        correct = (item.get("correctAlternative") or "").strip().upper()
        if not year or not index or correct not in {"A", "B", "C", "D", "E"}:
            return False

        language = (item.get("language") or "").strip()
        question, created = self._get_or_build(item, year, index, correct, language)
        self._fill_question(question, item, correct, language, index)
        self.questions.flush()
        self._replace_options(question.id, item.get("alternatives") or [])
        return created

    def _get_or_build(self, item, year, index, correct, language) -> tuple[Question, bool]:
        question = self.questions.find_enem(year, index, language)
        if question:
            return question, False
        discipline = item.get("discipline")
        subject = DISCIPLINE_TO_SUBJECT.get(discipline or "", discipline or "Outros")
        question = Question(
            year=year,
            subject=subject,
            statement=_statement_from(item),
            correct_option=correct,
            explanation_text=DEFAULT_ENEM_EXPLANATION,
            source="enem-api",
            language=language,
            enem_index=index,
        )
        self.questions.add(question)
        return question, True

    def _fill_question(
        self, question: Question, item: dict, correct: str, language: str, index
    ) -> None:
        discipline = item.get("discipline")
        files = item.get("files") or []
        if not isinstance(files, list):
            files = []
        question.subject = DISCIPLINE_TO_SUBJECT.get(discipline or "", discipline or "Outros")
        question.discipline = discipline
        question.statement = _statement_from(item)
        question.image_url = files[0] if files else None
        question.correct_option = correct
        question.explanation_text = DEFAULT_ENEM_EXPLANATION
        question.context = item.get("context")
        question.files_json = json.dumps(files)
        question.alternatives_introduction = item.get("alternativesIntroduction")
        question.enem_title = item.get("title")
        question.language = language
        question.enem_index = index
        question.source = "enem-api"

    def _replace_options(self, question_id: int, alternatives: list) -> None:
        self.options.delete_for_question(question_id)
        for alternative in alternatives:
            letter = (alternative.get("letter") or "").strip().upper()
            if letter not in {"A", "B", "C", "D", "E"}:
                continue
            self.options.add(
                QuestionOption(
                    question_id=question_id,
                    letter=letter,
                    text=alternative.get("text") or "",
                    file_url=alternative.get("file"),
                )
            )

def _api_base() -> str:
    return current_app.config.get("ENEM_API_BASE", "https://api.enem.dev/v1").rstrip("/")

def _read_json(url: str, timeout: int) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "ProENEM-Lab/1.0"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def _retry_wait(err: urllib.error.HTTPError, attempt: int) -> float:
    wait = 2**attempt
    retry_after = err.headers.get("Retry-After") if err.headers else None
    if not retry_after:
        logger.warning("enem-api rate limited; retry in %ss", wait)
        return wait
    try:
        wait = max(wait, float(retry_after))
    except ValueError:
        pass
    logger.warning("enem-api rate limited; retry in %ss", wait)
    return wait

def _extract_questions(payload: Any) -> list[dict]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    for key in ("questions", "items", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []

def _statement_from(item: dict) -> str:
    context = (item.get("context") or "").strip()
    intro = (item.get("alternativesIntroduction") or "").strip()
    title = (item.get("title") or "").strip()
    if context:
        return context if not intro else f"{context}\n\n{intro}"
    if intro:
        return intro
    return title or f"Questão {item.get('index', '')}".strip()
