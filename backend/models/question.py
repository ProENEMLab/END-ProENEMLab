from __future__ import annotations

import json

from extensions import db

SOURCE_ATTRIBUTION = {
    "name": "ENEM/INEP",
    "via": "enem-api",
    "license": "GPL-2.0",
    "url": "https://enem.dev",
}

DEFAULT_ENEM_EXPLANATION = (
    "Gabarito oficial do ENEM (INEP). Fonte: enem-api (https://enem.dev), "
    "licença GPL-2.0. Comentário pedagógico não disponível nesta questão."
)

class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    subject = db.Column(db.String(80), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=True, index=True)
    statement = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    correct_option = db.Column(db.String(1), nullable=False)
    explanation_text = db.Column(db.Text, nullable=False)
    explanation_image_url = db.Column(db.String(255), nullable=True)
    explanation_video_url = db.Column(db.String(255), nullable=True)
    enem_index = db.Column(db.Integer, nullable=True, index=True)
    language = db.Column(db.String(32), nullable=False, default="", server_default="")
    discipline = db.Column(db.String(40), nullable=True)
    context = db.Column(db.Text, nullable=True)
    files_json = db.Column(db.Text, nullable=True)
    alternatives_introduction = db.Column(db.Text, nullable=True)
    enem_title = db.Column(db.String(255), nullable=True)
    source = db.Column(
        db.String(32), nullable=False, default="seed", server_default="seed", index=True
    )
    inep_item_code = db.Column(db.String(64), nullable=True, index=True)
    difficulty = db.Column(db.String(16), nullable=True)
    enem_correct_rate = db.Column(db.Float, nullable=True)
    difficulty_source = db.Column(db.String(16), nullable=True)
    difficulty_value = db.Column(db.Float, nullable=True)
    difficulty_updated_at = db.Column(db.DateTime, nullable=True)

    topic = db.relationship("Topic", back_populates="questions")
    options = db.relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.letter",
    )
    attempts = db.relationship("Attempt", back_populates="question", lazy="dynamic")

    @property
    def files(self) -> list[str]:
        if not self.files_json:
            return []
        try:
            data = json.loads(self.files_json)
        except json.JSONDecodeError:
            return []
        return data if isinstance(data, list) else []

    def _attribution(self) -> dict | None:
        if self.source == "enem-api":
            return SOURCE_ATTRIBUTION
        return None

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "year": self.year,
            "subject": self.subject,
            "topic_id": self.topic_id,
            "statement": self.statement,
            "image_url": self.image_url,
            "enem_index": self.enem_index,
            "language": self.language or None,
            "discipline": self.discipline,
            "context": self.context,
            "files": self.files,
            "alternatives_introduction": self.alternatives_introduction,
            "enem_title": self.enem_title,
            "source": self.source,
            "difficulty": self.difficulty_payload(),
            "attribution": self._attribution(),
            "options": [opt.to_dict() for opt in self.options],
        }

    def to_list_dict(self) -> dict:
        return {
            "id": self.id,
            "year": self.year,
            "subject": self.subject,
            "topic_id": self.topic_id,
            "statement": self.statement,
            "image_url": self.image_url,
            "enem_index": self.enem_index,
            "language": self.language or None,
            "enem_title": self.enem_title,
            "source": self.source,
            "difficulty": self.difficulty_payload(),
        }

    def difficulty_payload(self) -> dict:
        labels = {"easy": "Fácil", "medium": "Médio", "hard": "Difícil"}
        if self.difficulty not in labels:
            return {"level": None, "source": None, "label": "Não classificada"}
        return {
            "level": self.difficulty,
            "source": self.difficulty_source,
            "label": labels[self.difficulty],
        }

class QuestionOption(db.Model):
    __tablename__ = "question_options"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    letter = db.Column(db.String(1), nullable=False)
    text = db.Column(db.Text, nullable=False)
    file_url = db.Column(db.Text, nullable=True)

    question = db.relationship("Question", back_populates="options")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "letter": self.letter,
            "text": self.text,
            "file_url": self.file_url,
        }
