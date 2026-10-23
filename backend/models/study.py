from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class StudyBlock(db.Model):
    __tablename__ = "study_blocks"
    __table_args__ = (db.Index("ix_study_blocks_user_week", "user_id", "week_start"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False, index=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_minute = db.Column(db.Integer, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    subject = db.relationship("Subject")

class PomodoroSettings(db.Model):
    __tablename__ = "pomodoro_settings"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    focus_minutes = db.Column(db.Integer, nullable=False, default=25)
    short_break_minutes = db.Column(db.Integer, nullable=False, default=5)
    long_break_minutes = db.Column(db.Integer, nullable=False, default=15)
    cycles_before_long_break = db.Column(db.Integer, nullable=False, default=4)
    auto_start_blocks = db.Column(db.Boolean, nullable=False, default=True)
    focus_mode_enabled = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    focus_mode_fullscreen = db.Column(db.Boolean, nullable=False, default=True, server_default="1")
    focus_mode_sound = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    @classmethod
    def create_default(cls, user_id: int, updated_at):
        return cls(
            user_id=user_id,
            focus_minutes=25,
            short_break_minutes=5,
            long_break_minutes=15,
            cycles_before_long_break=4,
            auto_start_blocks=True,
            focus_mode_enabled=False,
            focus_mode_fullscreen=True,
            focus_mode_sound=False,
            updated_at=updated_at,
        )

    def to_dict(self) -> dict:
        fullscreen = self.focus_mode_fullscreen
        return {
            "focus_minutes": self.focus_minutes,
            "short_break_minutes": self.short_break_minutes,
            "long_break_minutes": self.long_break_minutes,
            "cycles_before_long_break": self.cycles_before_long_break,
            "auto_start_blocks": bool(self.auto_start_blocks),
            "focus_mode_enabled": bool(self.focus_mode_enabled),
            "focus_mode_fullscreen": True if fullscreen is None else bool(fullscreen),
            "focus_mode_sound": bool(self.focus_mode_sound),
        }

class StudySession(db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id"), nullable=False)
    block_id = db.Column(
        db.Integer,
        db.ForeignKey("study_blocks.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = db.Column(db.String(16), nullable=False, default="running")
    planned_cycles = db.Column(db.Integer, nullable=False)
    completed_cycles = db.Column(db.Integer, nullable=False, default=0)
    started_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    focused_seconds = db.Column(db.Integer, nullable=False, default=0)

    subject = db.relationship("Subject")
    intervals = db.relationship("FocusInterval", backref="session", order_by="FocusInterval.id")

class FocusInterval(db.Model):
    __tablename__ = "focus_intervals"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("study_sessions.id"),
        nullable=False,
        index=True,
    )
    cycle_number = db.Column(db.Integer, nullable=False)
    started_at = db.Column(db.DateTime, nullable=False)
    ended_at = db.Column(db.DateTime, nullable=True)

class WeeklyReport(db.Model):

    __tablename__ = "weekly_reports"
    __table_args__ = (
        db.UniqueConstraint("user_id", "week_start", name="uq_weekly_report_user_week"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    week_start = db.Column(db.Date, nullable=False)
    payload = db.Column(db.Text, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False)

class FocusInterruption(db.Model):

    __tablename__ = "focus_interruptions"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer,
        db.ForeignKey("study_sessions.id"),
        nullable=False,
        index=True,
    )
    kind = db.Column(db.String(32), nullable=False)
    occurred_at = db.Column(db.DateTime, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=True)
