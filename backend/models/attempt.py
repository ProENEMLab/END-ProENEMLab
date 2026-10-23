from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

ERROR_TYPES = ("conceito", "atencao")

class Attempt(db.Model):
    __tablename__ = "attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    selected_option = db.Column(db.String(1), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    error_type = db.Column(db.String(32), nullable=True)
    answered_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="attempts")
    question = db.relationship("Question", back_populates="attempts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "question_id": self.question_id,
            "selected_option": self.selected_option,
            "is_correct": self.is_correct,
            "error_type": self.error_type,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }
