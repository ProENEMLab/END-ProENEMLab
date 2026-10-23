from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

POINT_REASONS = (
    "question_answered",
    "goal_completed",
    "streak_bonus",
    "pomodoro_completed",
)

POINT_VALUES = {
    "question_answered": 5,
    "goal_completed": 15,
    "streak_bonus": 20,
    "pomodoro_completed": 10,
}

class PointsTransaction(db.Model):
    __tablename__ = "points_transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    points = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(64), nullable=False)
    reference_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="points_transactions")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "points": self.points,
            "reason": self.reason,
            "reference_id": self.reference_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class DailyGoal(db.Model):
    __tablename__ = "daily_goals"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    description = db.Column(db.String(255), nullable=False)
    target_date = db.Column(db.Date, nullable=False, index=True)
    is_completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User", back_populates="daily_goals")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "description": self.description,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "is_completed": self.is_completed,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class StreakRecord(db.Model):
    __tablename__ = "streak_records"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    current_streak = db.Column(db.Integer, nullable=False, default=0)
    longest_streak = db.Column(db.Integer, nullable=False, default=0)
    last_activity_date = db.Column(db.Date, nullable=True)

    user = db.relationship("User", back_populates="streak_record")

    def to_dict(self) -> dict:
        return {
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "last_activity_date": (
                self.last_activity_date.isoformat() if self.last_activity_date else None
            ),
        }
