from datetime import datetime, timezone

from sqlalchemy import Index, text

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class UserTopicLevel(db.Model):

    __tablename__ = "user_topic_levels"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), primary_key=True)
    unlocked_level = db.Column(
        db.String(16), nullable=False, default="easy", server_default="easy"
    )
    unlocked_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "unlocked_level": self.unlocked_level,
            "unlocked_at": self.unlocked_at.isoformat() if self.unlocked_at else None,
        }

class TopicProgression(db.Model):
    __tablename__ = "topic_progressions"
    __table_args__ = (db.UniqueConstraint("user_id", "topic_id", name="uq_progression_user_topic"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), nullable=False, index=True)
    unlocked_level = db.Column(db.String(16), nullable=False, default="easy")

    def to_dict(self) -> dict:
        return {
            "topic_id": self.topic_id,
            "unlocked_level": self.unlocked_level,
        }

class ReviewItem(db.Model):
    __tablename__ = "review_items"
    __table_args__ = (
        db.UniqueConstraint("user_id", "question_id", name="uq_review_user_question"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    error_on = db.Column(db.Date, nullable=False)
    stage_index = db.Column(db.Integer, nullable=False, default=0)
    due_on = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default="scheduled")
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    question = db.relationship("Question")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question_id": self.question_id,
            "error_on": self.error_on.isoformat() if self.error_on else None,
            "stage_index": self.stage_index,
            "due_on": self.due_on.isoformat() if self.due_on else None,
            "status": self.status,
        }

class ReviewCycle(db.Model):

    __tablename__ = "review_cycles"
    __table_args__ = (
        Index("ix_review_cycles_user_status_due", "user_id", "status", "due_date"),
        Index(
            "uq_review_cycles_one_active",
            "user_id",
            "question_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
            postgresql_where=text("status = 'active'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default="active")
    anchor_date = db.Column(db.Date, nullable=False)
    current_stage = db.Column(db.Integer, nullable=False, default=1)
    due_date = db.Column(db.Date, nullable=False)
    restart_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)

    question = db.relationship("Question")
    events = db.relationship(
        "ReviewEvent",
        back_populates="cycle",
        cascade="all, delete-orphan",
        order_by="ReviewEvent.id",
    )

class ReviewEvent(db.Model):

    __tablename__ = "review_events"

    id = db.Column(db.Integer, primary_key=True)
    cycle_id = db.Column(db.Integer, db.ForeignKey("review_cycles.id"), nullable=False, index=True)
    stage = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(32), nullable=False)
    attempt_id = db.Column(db.Integer, db.ForeignKey("attempts.id"), nullable=True)
    occurred_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    cycle = db.relationship("ReviewCycle", back_populates="events")
