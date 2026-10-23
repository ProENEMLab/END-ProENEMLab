from io import BytesIO
from pathlib import Path

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
)

from services.pdf.markup import escape_text, to_markup
from services.study_report_document import (
    ReportImage,
    ReportTopicNotes,
    ReportWrongQuestion,
    StudyReportDocument,
)

_FONTS = Path(__file__).resolve().parent / "fonts"
_fonts_ready = False
_MARGIN_X = 18 * mm
_MARGIN_TOP = 18 * mm
_MARGIN_BOTTOM = 16 * mm

def render_study_report(document: StudyReportDocument) -> bytes:
    _ensure_fonts()
    marks: dict[str, int] = {}
    total: int | None = None
    pdf = b""
    for _ in range(4):
        pdf, new_marks, new_total = _build(document, marks, total)
        if new_marks == marks and new_total == total:
            return pdf
        marks = new_marks
        total = new_total
    return pdf

def _build(
    document: StudyReportDocument, marks: dict[str, int], total: int | None
) -> tuple[bytes, dict[str, int], int]:
    buffer = BytesIO()
    doc = _ReportDoc(
        buffer,
        user_name=document.user_name,
        total_pages=total,
        pagesize=A4,
        leftMargin=_MARGIN_X,
        rightMargin=_MARGIN_X,
        topMargin=_MARGIN_TOP,
        bottomMargin=_MARGIN_BOTTOM,
        title="Relatório de estudos — ProENEM Lab",
    )
    styles = _styles()
    story = _story(document, styles, marks, doc.width)
    doc.build(story)
    return buffer.getvalue(), dict(doc.marks), doc.page

class _ReportDoc(BaseDocTemplate):

    def __init__(self, buffer, user_name: str, total_pages: int | None, **kwargs):
        super().__init__(buffer, **kwargs)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self._footer)])
        self.user_name = user_name
        self.total_pages = total_pages
        self.marks: dict[str, int] = {}

    def afterFlowable(self, flowable):
        key = getattr(flowable, "mark_key", None)
        if key:
            self.marks[key] = self.page

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("DejaVu", 8)
        canvas.setFillColorRGB(0.25, 0.28, 0.33)
        total = self.total_pages if self.total_pages else "..."
        name = self.user_name if len(self.user_name) <= 80 else f"{self.user_name[:77]}..."
        label = f"ProENEM Lab · {name} · página {doc.page} de {total}"
        canvas.drawCentredString(A4[0] / 2, 8 * mm, label)
        canvas.restoreState()

def _story(document: StudyReportDocument, styles: dict, marks: dict[str, int], width: float):
    story = []
    story.extend(_cover(document, styles))
    story.append(PageBreak())
    story.extend(_summary(document, styles))
    story.append(PageBreak())
    story.extend(_toc(document, styles, marks, width))
    if document.include_notes and document.note_sections:
        story.append(PageBreak())
        story.append(_marked("Parte 1 — Anotações por tópico", styles["h1"], "part-notes"))
        story.append(Spacer(1, 4 * mm))
        for section in document.note_sections:
            story.extend(_notes_section(section, styles))
    if document.include_wrongs and document.wrong_groups:
        story.append(PageBreak())
        story.append(
            _marked("Parte 2 — Questões erradas com gabarito comentado", styles["h1"], "part-wrong")
        )
        story.append(Spacer(1, 4 * mm))
        for group in document.wrong_groups:
            story.append(_marked(group.title, styles["h2"], group.key))
            for question in group.questions:
                story.extend(_question_block(question, styles, width))
    return story

def _cover(document: StudyReportDocument, styles: dict):
    block = [
        Spacer(1, 28 * mm),
        Paragraph("Relatório de estudos — ProENEM Lab", styles["cover"]),
        Spacer(1, 10 * mm),
        Paragraph(escape_text(document.user_name), styles["cover_sub"]),
        Spacer(1, 6 * mm),
        Paragraph(f"Gerado em {escape_text(document.generated_label)}", styles["meta"]),
        Paragraph(f"Período: {escape_text(document.period_label)}", styles["meta"]),
    ]
    for warning in document.warnings:
        block.append(Spacer(1, 4 * mm))
        block.append(Paragraph(escape_text(warning), styles["warning"]))
    return block

def _summary(document: StudyReportDocument, styles: dict):
    rows = [
        ("Anotações", str(document.notes_count)),
        ("Tópicos com anotação", str(document.topics_with_notes)),
        ("Questões erradas", str(document.wrong_count)),
        ("Erradas que você acertou depois", str(document.resolved_count)),
        ("Acerto geral", document.accuracy_label),
    ]
    story = [Paragraph("Resumo", styles["h1"]), Spacer(1, 4 * mm)]
    for label, value in rows:
        story.append(
            Paragraph(f"<b>{escape_text(label)}:</b> {escape_text(value)}", styles["body"])
        )
    return story

def _toc(document: StudyReportDocument, styles: dict, marks: dict[str, int], width: float):
    story = [Paragraph("Sumário", styles["h1"]), Spacer(1, 4 * mm)]
    entries = document.toc()
    if not entries:
        story.append(Paragraph("Nenhuma seção neste recorte.", styles["body"]))
        return story
    page_col = 18 * mm
    for entry in entries:
        title_style = styles["toc"] if entry.level == 0 else styles["toc_sub"]
        page = marks.get(entry.key)
        page_label = str(page) if page else "—"
        table = Table(
            [
                [
                    Paragraph(escape_text(entry.title), title_style),
                    Paragraph(page_label, styles["toc_page"]),
                ]
            ],
            colWidths=[width - page_col, page_col],
        )
        table.setStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
        story.append(table)
    return story

def _notes_section(section: ReportTopicNotes, styles: dict):
    if section.topic_name == "Sem tópico" and section.position is None:
        title = "Sem tópico"
        meta = ""
    else:
        title = f"{section.subject_name} › {section.topic_name}"
        meta = f"Posição no roadmap: {section.position} · Status: {section.status_label}"
    story = [_marked(title, styles["h2"], section.key)]
    if meta:
        story.append(Paragraph(escape_text(meta), styles["meta"]))
    story.append(Spacer(1, 2 * mm))
    for note in section.notes:
        created = note.created_label
        updated = note.updated_label
        if created == updated:
            when = f"Criada em {created}"
        else:
            when = f"Criada em {created} · Editada em {updated}"
        story.append(Paragraph(escape_text(when), styles["meta"]))
        story.append(Paragraph(to_markup(note.content), styles["body"]))
        story.append(Spacer(1, 3 * mm))
    return story

def _question_block(question: ReportWrongQuestion, styles: dict, width: float):
    story = [
        Paragraph(escape_text(question.heading), styles["h3"]),
        Paragraph(to_markup(question.statement), styles["body"]),
    ]
    if question.context:
        story.append(
            Paragraph(f"<b>Texto-base</b><br/>{to_markup(question.context)}", styles["body"])
        )
    story.extend(_images(question.images, styles, width))
    if question.alternatives_introduction:
        story.append(Paragraph(to_markup(question.alternatives_introduction), styles["body"]))
    for option in question.options:
        story.append(
            Paragraph(
                f"<b>{escape_text(option.letter)})</b> {to_markup(option.text)}", styles["body"]
            )
        )
    story.append(
        Paragraph(
            f"<b>Sua resposta (última errada):</b> {escape_text(question.user_answer)}",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"<b>Alternativa correta:</b> {escape_text(question.correct_answer)}", styles["body"]
        )
    )
    story.append(
        Paragraph(f"<b>Explicação</b><br/>{to_markup(question.explanation)}", styles["body"])
    )
    story.extend(_images(question.explanation_images, styles, width))
    if question.video_url:
        visible = escape_text(question.video_url)
        href = escape_text(question.video_url).replace('"', "%22")
        story.append(
            Paragraph(f'<b>Vídeo:</b> <link href="{href}">{visible}</link>', styles["body"])
        )
    story.append(
        Paragraph(
            f"Tentativas: {question.attempt_count} · {escape_text(question.resolved_label)}",
            styles["meta"],
        )
    )
    if question.review_label:
        story.append(Paragraph(f"Revisão: {escape_text(question.review_label)}", styles["meta"]))
    story.append(Spacer(1, 5 * mm))
    return story

def _images(images: list[ReportImage], styles: dict, width: float):
    story = []
    for image in images:
        if image.data:
            drawn = _fitted_image(image.data, width)
            if drawn is not None:
                story.append(Spacer(1, 2 * mm))
                story.append(drawn)
                story.append(Spacer(1, 2 * mm))
                continue
        if image.placeholder:
            story.append(Paragraph(escape_text(image.placeholder), styles["meta"]))
    return story

def _fitted_image(data: bytes, width: float):
    try:
        reader = ImageReader(BytesIO(data))
        pixel_w, pixel_h = reader.getSize()
    except Exception:
        return None
    if not pixel_w or not pixel_h:
        return None
    max_h = 70 * mm
    scale = min(width / float(pixel_w), max_h / float(pixel_h), 1)
    return Image(BytesIO(data), width=pixel_w * scale, height=pixel_h * scale)

def _marked(text: str, style: ParagraphStyle, key: str) -> Paragraph:
    flowable = Paragraph(escape_text(text), style)
    flowable.mark_key = key
    return flowable

def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName="DejaVu", textColor="#1c2430", leading=14)
    return {
        "cover": ParagraphStyle(
            "cover",
            fontName="DejaVu-Bold",
            fontSize=22,
            leading=28,
            alignment=TA_CENTER,
            textColor="#10233f",
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub",
            fontName="DejaVu",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
            textColor="#1c2430",
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName="DejaVu-Bold",
            fontSize=16,
            leading=20,
            spaceAfter=2 * mm,
            textColor="#10233f",
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName="DejaVu-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=4 * mm,
            spaceAfter=1 * mm,
            textColor="#10233f",
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="DejaVu-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=3 * mm,
            spaceAfter=1 * mm,
            textColor="#1c2430",
        ),
        "body": ParagraphStyle("body", fontSize=10, alignment=TA_LEFT, spaceAfter=1.5 * mm, **base),
        "meta": ParagraphStyle(
            "meta",
            fontSize=9,
            leading=12,
            textColor="#4b5565",
            spaceAfter=1 * mm,
            fontName="DejaVu",
        ),
        "warning": ParagraphStyle(
            "warning", fontSize=10, leading=13, textColor="#8a4b08", fontName="DejaVu"
        ),
        "toc": ParagraphStyle(
            "toc", fontName="DejaVu-Bold", fontSize=11, leading=14, textColor="#10233f"
        ),
        "toc_sub": ParagraphStyle(
            "toc_sub",
            fontName="DejaVu",
            fontSize=10,
            leading=13,
            leftIndent=4 * mm,
            textColor="#1c2430",
        ),
        "toc_page": ParagraphStyle(
            "toc_page",
            fontName="DejaVu",
            fontSize=10,
            leading=13,
            alignment=TA_RIGHT,
            textColor="#1c2430",
        ),
    }

def _ensure_fonts() -> None:
    global _fonts_ready
    if _fonts_ready:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", str(_FONTS / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(_FONTS / "DejaVuSans-Bold.ttf")))
    _fonts_ready = True
