from collections import defaultdict

from services.exceptions import ExportError
from services.simple_pdf import render_pdf
from models.attempt import Attempt
from models.question import Question
from repositories.notification_repository import ExportRepository
from repositories.topic_repository import TopicRepository

class ExportService:

    def __init__(
        self,
        export_repository: ExportRepository,
        topic_repository: TopicRepository,
    ) -> None:
        self.exports = export_repository
        self.topics = topic_repository

    def study_pdf(self, user_id: int) -> bytes:
        lines = ["# ProENEM Lab — material de estudo", ""]
        lines.extend(self._notes(user_id))
        lines.extend(self._wrongs(user_id))
        pdf = render_pdf(lines)
        if not pdf.startswith(b"%PDF"):
            raise ExportError("Could not build the PDF.", 500, "PDF_FAILED")
        return pdf

    def _notes(self, user_id: int) -> list[str]:
        notes = self.exports.list_notes(user_id)
        lines = ["# Anotações por tópico", ""]
        if not notes:
            return lines + ["Nenhuma anotação ainda.", ""]
        names = {topic.id: topic.name for topic in self.topics.list_ordered()}
        grouped: dict[str, list[str]] = defaultdict(list)
        for note in notes:
            grouped[names.get(note.topic_id, "Tópico")].append(note.content.strip())
        for topic_name in sorted(grouped):
            lines.append(topic_name)
            for content in grouped[topic_name]:
                lines.extend(_wrap(content))
            lines.append("")
        return lines

    def _wrongs(self, user_id: int) -> list[str]:
        lines = ["# Questões erradas", ""]
        latest: dict[int, Attempt] = {}
        rows = Attempt.query.filter_by(user_id=user_id).order_by(Attempt.answered_at.asc()).all()
        for row in rows:
            latest[row.question_id] = row
        wrongs = [row for row in latest.values() if not row.is_correct]
        if not wrongs:
            return lines + ["Nenhuma questão errada em aberto.", ""]
        for attempt in wrongs:
            question = attempt.question or Question.query.get(attempt.question_id)
            if not question:
                continue
            lines.append(f"Questão {question.id} · {question.subject} · {question.year}")
            lines.extend(_wrap(question.statement))
            lines.append(f"Sua resposta: {attempt.selected_option}")
            lines.append(f"Gabarito: {question.correct_option}")
            lines.extend(_wrap(question.explanation_text))
            lines.append("")
        return lines

def _wrap(text: str, width: int = 90) -> list[str]:
    words = (text or "").replace("\n", " ").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) > width:
            if current:
                lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines
