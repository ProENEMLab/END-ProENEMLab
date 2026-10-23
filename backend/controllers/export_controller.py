from datetime import datetime
from io import BytesIO

from flask import request, send_file

from controllers.http import current_user_id
from services.exceptions import ExportError
from services.study_report_service import StudyReportFilters, StudyReportService

_SECTIONS = {"notes", "wrong"}
_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

class StudyReportController:

    def __init__(self, service: StudyReportService) -> None:
        self.service = service

    def download(self):
        pdf, filename = self.service.export(current_user_id(), self._filters())
        return send_file(
            BytesIO(pdf),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    def _filters(self) -> StudyReportFilters:
        return StudyReportFilters(
            sections=self._sections(),
            subject_id=self._subject_id(),
            date_from=self._date("from"),
            date_to=self._date("to"),
            include_resolved=self._flag("include_resolved", default=True),
        )

    def _sections(self) -> frozenset[str]:
        raw = request.args.get("sections")
        if _query_blank(raw):
            if "sections" in request.args:
                raise ExportError(
                    "Informe ao menos uma seção: notes ou wrong.", 400, "VALIDATION_ERROR"
                )
            return frozenset(_SECTIONS)
        return _parse_sections(raw)

    def _subject_id(self) -> int | None:
        raw = request.args.get("subject_id")
        if raw is None or raw.strip() == "":
            return None
        if not raw.strip().isdigit():
            raise ExportError("subject_id deve ser um número.", 400, "VALIDATION_ERROR")
        return int(raw)

    def _date(self, name: str):
        parsed = _iso_date(request.args.get(name))
        if parsed is None:
            return None
        if name == "from":
            _check_range(parsed, request.args.get("to"))
        return parsed

    def _flag(self, name: str, default: bool) -> bool:
        raw = request.args.get(name)
        if raw is None or raw.strip() == "":
            return default
        value = raw.strip().lower()
        if value in _TRUE:
            return True
        if value in _FALSE:
            return False
        raise ExportError("include_resolved deve ser true ou false.", 400, "VALIDATION_ERROR")

def _query_blank(raw) -> bool:
    if raw is None:
        return True
    return raw.strip() == ""

def _parse_sections(raw) -> frozenset[str]:
    parts = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            parts.append(part)
    if not parts:
        raise ExportError("Seção desconhecida. Use notes ou wrong.", 400, "VALIDATION_ERROR")
    for part in parts:
        if part not in _SECTIONS:
            raise ExportError("Seção desconhecida. Use notes ou wrong.", 400, "VALIDATION_ERROR")
    return frozenset(parts)

def _iso_date(raw):
    if _query_blank(raw):
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError as err:
        raise ExportError("Data inválida. Use AAAA-MM-DD.", 400, "VALIDATION_ERROR") from err

def _check_range(start, other_raw):
    if not other_raw:
        return
    try:
        other = datetime.strptime(other_raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return
    if start > other:
        raise ExportError("A data inicial é posterior à data final.", 400, "VALIDATION_ERROR")

from flask import Blueprint
from flask_jwt_extended import jwt_required

study_report_bp = Blueprint("study_report_exports", __name__, url_prefix="/api/exports")

def bind_export_routes() -> None:
    if getattr(bind_export_routes, "done", False):
        return
    bind_export_routes.done = True
    from container import study_report_controller
    study_report_bp.get("/study-report.pdf")(jwt_required()(study_report_controller.download))
