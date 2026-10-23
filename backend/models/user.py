from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires_at = db.Column(db.DateTime, nullable=True)
    total_points = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    topic_progress = db.relationship("UserTopicProgress", back_populates="user", lazy="dynamic")
    notes = db.relationship("Note", back_populates="user", lazy="dynamic")
    attempts = db.relationship("Attempt", back_populates="user", lazy="dynamic")
    daily_goals = db.relationship("DailyGoal", back_populates="user", lazy="dynamic")
    points_transactions = db.relationship(
        "PointsTransaction", back_populates="user", lazy="dynamic"
    )
    streak_record = db.relationship("StreakRecord", back_populates="user", uselist=False)
    saved_filter_sets = db.relationship(
        "SavedFilterSet", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "total_points": self.total_points,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
