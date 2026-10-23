import json
from datetime import datetime, timezone

from sqlalchemy import Index, text

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class NotificationPreference(db.Model):

    __tablename__ = "notification_preferences"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    email_enabled = db.Column(db.Boolean, nullable=False, default=False)
    push_enabled = db.Column(db.Boolean, nullable=False, default=False)
    types = db.Column(db.Text, nullable=False, default="{}")
    quiet_start = db.Column(db.String(5), nullable=False, default="22:00")
    quiet_end = db.Column(db.String(5), nullable=False, default="07:00")
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def parsed_types(self) -> dict:
        try:
            data = json.loads(self.types or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    def to_dict(self) -> dict:
        return {
            "email_enabled": bool(self.email_enabled),
            "push_enabled": bool(self.push_enabled),
            "quiet_start": self.quiet_start,
            "quiet_end": self.quiet_end,
            "types": self.parsed_types(),
        }

class PushSubscription(db.Model):

    __tablename__ = "push_subscriptions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    endpoint = db.Column(db.Text, unique=True, nullable=False)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    last_success_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "endpoint": self.endpoint,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_success_at": (self.last_success_at.isoformat() if self.last_success_at else None),
        }

class NotificationLog(db.Model):

    __tablename__ = "notification_log"
    __table_args__ = (
        Index(
            "uq_notification_log_sent",
            "user_id",
            "type",
            "channel",
            "local_date",
            unique=True,
            sqlite_where=text("status = 'sent' AND type != 'test'"),
            postgresql_where=text("status = 'sent' AND type != 'test'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    type = db.Column(db.String(32), nullable=False)
    channel = db.Column(db.String(16), nullable=False)
    local_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(32), nullable=False)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "channel": self.channel,
            "local_date": self.local_date.isoformat() if self.local_date else None,
            "status": self.status,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class NotificationMessage(db.Model):

    __tablename__ = "notification_messages"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    channel = db.Column(db.String(16), nullable=False)
    kind = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    body = db.Column(db.Text, nullable=False)
    local_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(16), nullable=False, default="sent")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "local_date": self.local_date.isoformat() if self.local_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }

class InepRefresh(db.Model):
    __tablename__ = "inep_refreshes"

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True, nullable=False)
    exam_years = db.Column(db.String(64), nullable=False, default="")
    refreshed_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        years = [int(part) for part in self.exam_years.split(",") if part]
        return {
            "year": self.year,
            "exam_years": years,
            "refreshed_at": self.refreshed_at.isoformat() if self.refreshed_at else None,
        }
