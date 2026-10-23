from datetime import date, datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from services.clock import as_utc
from extensions import db
from models.note import Note
from models.notification import NotificationLog, NotificationPreference, PushSubscription
from repositories.base_repository import BaseRepository

class NotificationRepository(BaseRepository):

    model = NotificationLog

    def get_preference(self, user_id: int) -> NotificationPreference | None:
        return db.session.get(NotificationPreference, user_id)

    def list_with_channel_enabled(self) -> list[NotificationPreference]:
        return (
            NotificationPreference.query.filter(
                or_(
                    NotificationPreference.email_enabled.is_(True),
                    NotificationPreference.push_enabled.is_(True),
                )
            )
            .order_by(NotificationPreference.user_id.asc())
            .all()
        )

    def has_status(
        self, user_id: int, kind: str, channel: str, local_date: date, status: str
    ) -> bool:
        return (
            NotificationLog.query.filter_by(
                user_id=user_id,
                type=kind,
                channel=channel,
                local_date=local_date,
                status=status,
            ).first()
            is not None
        )

    def count_sent(self, user_id: int, local_date: date) -> int:
        return NotificationLog.query.filter(
            NotificationLog.user_id == user_id,
            NotificationLog.local_date == local_date,
            NotificationLog.status == "sent",
            NotificationLog.type != "test",
        ).count()

    def count_tests_since(self, user_id: int, since: datetime) -> int:
        since_utc = as_utc(since)
        rows = NotificationLog.query.filter_by(user_id=user_id, type="test").all()
        return sum(1 for row in rows if row.created_at and as_utc(row.created_at) >= since_utc)

    def add_log(self, row: NotificationLog) -> bool:
        try:
            with db.session.begin_nested():
                db.session.add(row)
                db.session.flush()
        except IntegrityError:
            return False
        return True

    def list_log(self, user_id: int, limit: int) -> list[NotificationLog]:
        return (
            NotificationLog.query.filter_by(user_id=user_id)
            .order_by(NotificationLog.created_at.desc(), NotificationLog.id.desc())
            .limit(limit)
            .all()
        )

    def get_subscription_by_endpoint(self, endpoint: str) -> PushSubscription | None:
        return PushSubscription.query.filter_by(endpoint=endpoint).first()

    def list_subscriptions(self, user_id: int) -> list[PushSubscription]:
        return (
            PushSubscription.query.filter_by(user_id=user_id)
            .order_by(PushSubscription.id.asc())
            .all()
        )

class ExportRepository(BaseRepository):

    model = Note

    def list_notes(self, user_id: int) -> list[Note]:
        return Note.query.filter_by(user_id=user_id).order_by(Note.updated_at.desc()).all()
