from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

TOPIC_STATUSES = ("not_started", "in_progress", "completed")

class Topic(db.Model):
    __tablename__ = "topics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    order_index = db.Column(db.Integer, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    inep_incidence = db.Column(db.Float, nullable=True)

    progress_entries = db.relationship("UserTopicProgress", back_populates="topic", lazy="dynamic")
    notes = db.relationship("Note", back_populates="topic", lazy="dynamic")
    questions = db.relationship("Question", back_populates="topic", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "order_index": self.order_index,
            "description": self.description,
            "inep_incidence": self.inep_incidence,
        }

class UserTopicProgress(db.Model):
    __tablename__ = "user_topic_progress"
    __table_args__ = (db.UniqueConstraint("user_id", "topic_id", name="uq_user_topic_progress"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False)
    status = db.Column(db.String(32), nullable=False, default="not_started")
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="topic_progress")
    topic = db.relationship("Topic", back_populates="progress_entries")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic_id": self.topic_id,
            "status": self.status,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
