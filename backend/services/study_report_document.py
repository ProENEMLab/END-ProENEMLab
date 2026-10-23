from dataclasses import dataclass, field

@dataclass
class ReportImage:

    data: bytes | None = None
    placeholder: str | None = None

@dataclass
class ReportNote:

    content: str
    created_label: str
    updated_label: str

@dataclass
class ReportTopicNotes:

    key: str
    subject_name: str
    topic_name: str
    position: int | None
    status_label: str
    notes: list[ReportNote]

@dataclass
class ReportOption:

    letter: str
    text: str

@dataclass
class ReportWrongQuestion:

    question_id: int
    heading: str
    statement: str
    context: str | None
    alternatives_introduction: str | None
    images: list[ReportImage]
    options: list[ReportOption]
    user_answer: str
    correct_answer: str
    explanation: str
    explanation_images: list[ReportImage]
    video_url: str | None
    attempt_count: int
    resolved_label: str
    review_label: str | None

@dataclass
class ReportWrongGroup:

    key: str
    title: str
    questions: list[ReportWrongQuestion]

@dataclass
class TocEntry:

    key: str
    title: str
    level: int

@dataclass
class StudyReportDocument:

    user_name: str
    generated_label: str
    period_label: str
    filename_date: str
    notes_count: int
    topics_with_notes: int
    wrong_count: int
    resolved_count: int
    accuracy_label: str
    include_notes: bool
    include_wrongs: bool
    note_sections: list[ReportTopicNotes] = field(default_factory=list)
    wrong_groups: list[ReportWrongGroup] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def toc(self) -> list[TocEntry]:
        entries: list[TocEntry] = []
        if self.include_notes and self.note_sections:
            entries.append(TocEntry("part-notes", "Parte 1 — Anotações por tópico", 0))
            for section in self.note_sections:
                entries.append(TocEntry(section.key, _topic_title(section), 1))
        if self.include_wrongs and self.wrong_groups:
            entries.append(TocEntry("part-wrong", "Parte 2 — Questões erradas", 0))
            for group in self.wrong_groups:
                entries.append(TocEntry(group.key, group.title, 1))
        return entries

def _topic_title(section: ReportTopicNotes) -> str:
    if section.position is None and section.topic_name == "Sem tópico":
        return "Sem tópico"
    return f"{section.subject_name} › {section.topic_name}"
