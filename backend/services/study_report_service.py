from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

from services.clock import Clock, app_timezone
from services.exceptions import ExportError
from models.note import Note
from models.question import Question, QuestionOption
from repositories.study_report_repository import StudyReportRepository
from repositories.user_repository import UserRepository
from services.export_rate_limiter import ExportRateLimiter
from services.study_report_document import (
    ReportImage,
    ReportNote,
    ReportOption,
    ReportTopicNotes,
    ReportWrongGroup,
    ReportWrongQuestion,
    StudyReportDocument,
)

PROGRESS_LABELS = {
    "not_started": "Não iniciado",
    "in_progress": "Em progresso",
    "completed": "Concluído",
}
REVIEW_LABELS = {
    "active": "Em revisão",
    "scheduled": "Revisão agendada",
    "completed": "Revisão concluída",
    "cancelled": "Revisão cancelada",
}
DIFFICULTY_LABELS = {"easy": "Fácil", "medium": "Médio", "hard": "Difícil"}
EMPTY_MESSAGE = "Você ainda não tem anotações nem questões erradas neste período"
_IMAGE_MARK = "[imagem disponível na plataforma]"
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ROOT = _BACKEND_ROOT.parent

@dataclass
class StudyReportFilters:

    sections: frozenset[str]
    subject_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    include_resolved: bool = True

class StudyReportService:

    def __init__(
        self,
        repository: StudyReportRepository,
        user_repository: UserRepository,
        clock: Clock,
        limiter: ExportRateLimiter,
    ) -> None:
        self.reports = repository
        self.users = user_repository
        self.clock = clock
        self.limiter = limiter

    def build(self, user_id: int, filters: StudyReportFilters) -> StudyReportDocument:
        user = self._require_user(user_id)
        subject_name = self._subject_name(filters.subject_id)
        zone = app_timezone()
        start, end = _bounds(filters.date_from, filters.date_to, zone)
        notes, wrongs, warnings = self._limited_rows(user_id, filters, subject_name, start, end)
        if not notes and not wrongs:
            raise ExportError(EMPTY_MESSAGE, 422, "NOTHING_TO_EXPORT")
        return self._document(user, user_id, filters, zone, subject_name, start, end, notes, wrongs, warnings)

    def _require_user(self, user_id):
        user = self.users.get_by_id(user_id)
        if user is None:
            raise ExportError("User not found.", 404, "USER_NOT_FOUND")
        return user

    def _limited_rows(self, user_id, filters, subject_name, start, end):
        notes = []
        wrongs = []
        warnings = []
        if "notes" in filters.sections:
            notes = self.reports.list_notes(user_id, subject_name, start, end)
            notes, warning = _cap_notes(notes)
            if warning:
                warnings.append(warning)
        if "wrong" in filters.sections:
            wrongs = self.reports.list_wrong_questions(
                user_id, subject_name, start, end, filters.include_resolved
            )
            wrongs, warning = _cap_wrongs(wrongs)
            if warning:
                warnings.append(warning)
        return notes, wrongs, warnings

    def _document(self, user, user_id, filters, zone, subject_name, start, end, notes, wrongs, warnings):
        positions = self.reports.roadmap_positions()
        progress = self.reports.progress_by_topic(user_id)
        note_sections = self._note_sections(notes, positions, progress, zone)
        wrong_groups = self._wrong_groups(wrongs, positions, zone)
        total, correct = self.reports.attempt_totals(user_id, subject_name, start, end)
        generated = self.clock.now_local()
        return StudyReportDocument(
            user_name=user.name,
            generated_label=generated.strftime("%d/%m/%Y %H:%M"),
            period_label=_period_label(filters.date_from, filters.date_to),
            filename_date=generated.strftime("%Y-%m-%d"),
            notes_count=sum(len(section.notes) for section in note_sections),
            topics_with_notes=_topics_with_notes(note_sections),
            wrong_count=sum(len(group.questions) for group in wrong_groups),
            resolved_count=_resolved_count(wrong_groups),
            accuracy_label=_accuracy(correct, total),
            include_notes="notes" in filters.sections,
            include_wrongs="wrong" in filters.sections,
            note_sections=note_sections,
            wrong_groups=wrong_groups,
            warnings=warnings,
        )

    def export(self, user_id: int, filters: StudyReportFilters) -> tuple[bytes, str]:
        self.limiter.hit(user_id, self.clock.now_utc())
        document = self.build(user_id, filters)
        from services.pdf.study_report_pdf import render_study_report

        pdf = render_study_report(document)
        if not pdf.startswith(b"%PDF"):
            raise ExportError("Could not build the PDF.", 500, "PDF_FAILED")
        filename = f"proenem-relatorio-{document.filename_date}.pdf"
        return pdf, filename

    def _subject_name(self, subject_id: int | None) -> str | None:
        if subject_id is None:
            return None
        subject = self.reports.get_subject(subject_id)
        if subject is None:
            raise ExportError("Disciplina não encontrada.", 400, "SUBJECT_NOT_FOUND")
        return subject.name

    def _note_sections(
        self,
        notes: list[Note],
        positions: list[tuple[int, int]],
        progress: dict[int, str],
        zone: ZoneInfo,
    ) -> list[ReportTopicNotes]:
        grouped = _group_notes(notes)
        sections: list[ReportTopicNotes] = []
        for topic_id, position in positions:
            section = _placed_notes(topic_id, position, grouped, progress, zone)
            if section:
                sections.append(section)
        loose = _loose_notes(grouped.get(None, []), zone)
        if loose:
            sections.append(loose)
        return sections

    def _wrong_groups(
        self,
        rows: list[dict],
        positions: list[tuple[int, int]],
        zone: ZoneInfo,
    ) -> list[ReportWrongGroup]:
        if not rows:
            return []
        options = self.reports.options_for([row["question"].id for row in rows])
        by_topic = _group_wrongs(rows)
        groups: list[ReportWrongGroup] = []
        for topic_id, position in positions:
            group = _placed_wrongs(topic_id, position, by_topic, options, zone)
            if group:
                groups.append(group)
        loose = _loose_wrongs(by_topic.get(None, []), options, zone)
        if loose:
            groups.append(loose)
        return groups

def _report_note(note: Note, zone: ZoneInfo) -> ReportNote:
    created = _local(note.created_at, zone)
    updated = _local(note.updated_at, zone) if note.updated_at else created
    return ReportNote(
        content=note.content,
        created_label=created.strftime("%d/%m/%Y %H:%M"),
        updated_label=updated.strftime("%d/%m/%Y %H:%M"),
    )

def _wrong_question(
    row: dict, options: list[QuestionOption], zone: ZoneInfo
) -> ReportWrongQuestion:
    question: Question = row["question"]
    by_letter = {option.letter: option.text for option in options}
    return ReportWrongQuestion(
        question_id=question.id,
        heading=_wrong_heading(question, row["topic"]),
        statement=question.statement or "",
        context=question.context,
        alternatives_introduction=question.alternatives_introduction,
        images=_kept_images(_statement_urls(question)),
        options=[_report_option(option) for option in options],
        user_answer=_choice(row["selected_option"], by_letter),
        correct_answer=_choice(question.correct_option, by_letter),
        explanation=question.explanation_text or "",
        explanation_images=_explanation_images(question),
        video_url=question.explanation_video_url,
        attempt_count=row["attempt_count"],
        resolved_label=_resolved_label(row["resolved_at"], zone),
        review_label=_review_label(row["review_status"]),
    )

def _choice(letter: str | None, by_letter: dict[str, str]) -> str:
    if not letter:
        return "—"
    text = by_letter.get(letter)
    if text:
        return f"{letter} — {text}"
    return letter

def _statement_urls(question: Question) -> list[str]:
    urls = []
    if question.image_url:
        urls.append(question.image_url)
    for item in question.files:
        if isinstance(item, str) and item not in urls:
            urls.append(item)
    return urls

def _load_image(url: str | None) -> ReportImage | None:
    if not url:
        return None
    path = _local_image_path(url)
    if path is None:
        return ReportImage(placeholder=_IMAGE_MARK)
    try:
        data = path.read_bytes()
    except OSError:
        return ReportImage(placeholder=_IMAGE_MARK)
    if not data:
        return ReportImage(placeholder=_IMAGE_MARK)
    return ReportImage(data=data)

def _local_image_path(url: str) -> Path | None:
    relative = _image_relative(url)
    if relative is None:
        return None
    return _safe_image_file(_image_candidate(relative))

def _image_relative(url: str):
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"}:
        return _http_image_path(parsed)
    if parsed.scheme not in {"", "file"}:
        return None
    raw = parsed.path or url
    return unquote(raw).replace("\\", "/")

def _http_image_path(parsed):
    host = parsed.hostname or ""
    if host.lower() not in {"localhost", "127.0.0.1", "::1"}:
        return None
    raw = parsed.path or ""
    return unquote(raw).replace("\\", "/")

def _image_candidate(relative: str) -> Path:
    if relative.startswith("/static/"):
        return _BACKEND_ROOT / "static" / relative[len("/static/") :]
    if relative.startswith("/assets/"):
        return _PROJECT_ROOT / "frontend" / "public" / relative.lstrip("/")
    if relative.startswith("/"):
        return _BACKEND_ROOT / relative.lstrip("/")
    return _BACKEND_ROOT / relative

def _safe_image_file(candidate: Path):
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not _inside_roots(resolved):
        return None
    if not resolved.is_file():
        return None
    return resolved

def _inside_roots(path: Path) -> bool:
    roots = (_BACKEND_ROOT.resolve(), (_PROJECT_ROOT / "frontend" / "public").resolve())
    for root in roots:
        if _is_inside(path, root):
            return True
    return False

def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

def _bounds(
    date_from: date | None, date_to: date | None, zone: ZoneInfo
) -> tuple[datetime | None, datetime | None]:
    start = None
    end = None
    if date_from is not None:
        start = datetime.combine(date_from, time.min, tzinfo=zone).astimezone(timezone.utc)
    if date_to is not None:
        end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=zone).astimezone(
            timezone.utc
        )
    return start, end

def _period_label(date_from: date | None, date_to: date | None) -> str:
    if date_from is None and date_to is None:
        return "Tudo"
    if date_from and date_to:
        return f"{date_from.strftime('%d/%m/%Y')} a {date_to.strftime('%d/%m/%Y')}"
    if date_from:
        return f"A partir de {date_from.strftime('%d/%m/%Y')}"
    return f"Até {date_to.strftime('%d/%m/%Y')}"

def _accuracy(correct: int, total: int) -> str:
    if not total:
        return "Sem tentativas"
    return f"{round(correct / total * 100)}%"

def _note_recent(note: Note):
    moment = note.updated_at or note.created_at
    return (_as_utc(moment), note.id)

def _as_utc(value: datetime) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def _local(value: datetime, zone: ZoneInfo) -> datetime:
    return _as_utc(value).astimezone(zone)

def _config_int(name: str, default: int) -> int:
    if has_app_context():
        return int(current_app.config.get(name, default))
    return default

def _cap_notes(notes):
    limit = _config_int("EXPORT_PDF_MAX_NOTES", 2000)
    if len(notes) <= limit:
        return notes, None
    notes = sorted(notes, key=_note_recent, reverse=True)[:limit]
    notes.sort(key=lambda note: (_as_utc(note.created_at), note.id))
    warning = (
        f"Relatório limitado às {limit} anotações mais recentes"
        " — use os filtros para exportar o restante"
    )
    return notes, warning

def _cap_wrongs(wrongs):
    limit = _config_int("EXPORT_PDF_MAX_QUESTIONS", 1000)
    if len(wrongs) <= limit:
        return wrongs, None
    wrongs = sorted(wrongs, key=lambda row: _as_utc(row["last_wrong_at"]), reverse=True)[:limit]
    warning = (
        f"Relatório limitado aos {limit} erros mais recentes"
        " — use os filtros para exportar o restante"
    )
    return wrongs, warning

def _topics_with_notes(sections) -> int:
    count = 0
    for section in sections:
        if section.position is not None:
            count += 1
    return count

def _resolved_count(groups) -> int:
    count = 0
    for group in groups:
        for item in group.questions:
            if item.resolved_label.startswith("Acertou"):
                count += 1
    return count

def _group_notes(notes):
    grouped: dict[int | None, list[Note]] = {}
    for note in notes:
        grouped.setdefault(note.topic_id, []).append(note)
    for bucket in grouped.values():
        bucket.sort(key=lambda note: (_as_utc(note.created_at), note.id))
    return grouped

def _placed_notes(topic_id, position, grouped, progress, zone):
    bucket = grouped.get(topic_id)
    if not bucket:
        return None
    topic = bucket[0].topic
    return ReportTopicNotes(
        key=f"notes-{topic_id}",
        subject_name=_label(topic, "subject", "Sem disciplina"),
        topic_name=_label(topic, "name", "Tópico"),
        position=position,
        status_label=PROGRESS_LABELS.get(progress.get(topic_id, "not_started"), "Não iniciado"),
        notes=[_report_note(note, zone) for note in bucket],
    )

def _loose_notes(notes, zone):
    if not notes:
        return None
    return ReportTopicNotes(
        key="notes-none",
        subject_name="",
        topic_name="Sem tópico",
        position=None,
        status_label="",
        notes=[_report_note(note, zone) for note in notes],
    )

def _label(topic, attr, fallback):
    if topic:
        return getattr(topic, attr)
    return fallback

def _group_wrongs(rows):
    by_topic: dict[int | None, list[dict]] = {}
    for row in rows:
        topic = row["topic"]
        key = topic.id if topic else None
        by_topic.setdefault(key, []).append(row)
    for bucket in by_topic.values():
        bucket.sort(key=lambda row: _as_utc(row["last_wrong_at"]), reverse=True)
    return by_topic

def _placed_wrongs(topic_id, position, by_topic, options, zone):
    bucket = by_topic.get(topic_id)
    if not bucket:
        return None
    return ReportWrongGroup(
        key=f"wrong-{topic_id}",
        title=_wrong_title(bucket[0]["topic"], position),
        questions=[_wrong_item(row, options, zone) for row in bucket],
    )

def _loose_wrongs(rows, options, zone):
    if not rows:
        return None
    return ReportWrongGroup(
        key="wrong-none",
        title="Sem tópico",
        questions=[_wrong_item(row, options, zone) for row in rows],
    )

def _wrong_title(topic, position):
    if topic:
        title = f"{topic.subject} › {topic.name}"
    else:
        title = "Sem tópico"
    return f"{title} · posição {position}"

def _wrong_item(row, options, zone):
    return _wrong_question(row, options.get(row["question"].id, []), zone)

def _wrong_heading(question, topic):
    bits = [f"{_origin(question)} {question.year}", question.subject]
    if topic is not None:
        bits.append(topic.name)
    difficulty = DIFFICULTY_LABELS.get(question.difficulty or "")
    if difficulty:
        bits.append(difficulty)
    return " · ".join(bits)

def _origin(question):
    if question.source in {"enem-api", "seed", "inep"}:
        return "ENEM"
    if question.source:
        return question.source
    return "Questão"

def _report_option(option):
    text = option.text or ""
    return ReportOption(letter=option.letter, text=text)

def _kept_images(urls):
    loaded = []
    for url in urls:
        image = _load_image(url)
        if image is not None:
            loaded.append(image)
    return loaded

def _explanation_images(question):
    if not question.explanation_image_url:
        return []
    return _kept_images([question.explanation_image_url])

def _resolved_label(resolved, zone):
    if not resolved:
        return "Ainda não acertou depois"
    return f"Acertou em {_local(resolved, zone).strftime('%d/%m/%Y')}"

def _review_label(status):
    if not status:
        return None
    return REVIEW_LABELS.get(status)
