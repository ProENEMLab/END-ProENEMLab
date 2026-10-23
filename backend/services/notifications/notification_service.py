import json
import logging
from datetime import timedelta

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

from services.clock import Clock
from services.exceptions import NotificationError
from models.notification import NotificationLog, NotificationPreference, PushSubscription
from repositories.calendar_repository import CalendarRepository
from repositories.notification_repository import NotificationRepository
from repositories.user_repository import UserRepository
from services.focus_service import FocusService
from services.goals_service import GoalsService
from services.notifications.catalog import (
    CHANNELS,
    LABELS,
    REMINDER_TYPES,
    TIMED_TYPES,
    default_preferences,
    default_types,
)
from services.notifications.schedule import in_quiet, parse_clock, reminder_moment, window_status
from services.notifications.templates import render
from services.review_service import ReviewService
from services.streak_service import StreakService

logger = logging.getLogger(__name__)

_TOKEN_SALT = "notification-unsubscribe"

class NotificationService:

    def __init__(
        self,
        notification_repository: NotificationRepository,
        user_repository: UserRepository,
        goals_service: GoalsService,
        review_service: ReviewService,
        streak_service: StreakService,
        focus_service: FocusService,
        calendar_repository: CalendarRepository,
        clock: Clock,
        email_sender,
        push_sender,
    ) -> None:
        self.notifications = notification_repository
        self.users = user_repository
        self.goals = goals_service
        self.reviews = review_service
        self.streaks = streak_service
        self.focus = focus_service
        self.calendar = calendar_repository
        self.clock = clock
        self.email_sender = email_sender
        self.push_sender = push_sender

    def get_preferences(self, user_id: int) -> dict:
        row = self.notifications.get_preference(user_id)
        if row is None:
            return default_preferences()
        payload = row.to_dict()
        payload["types"] = self._merged_types(row)
        return payload

    def update_preferences(self, user_id: int, payload: dict) -> dict:
        types = self._validate_types(payload["types"])
        quiet_start = self._require_clock(payload["quiet_start"])
        quiet_end = self._require_clock(payload["quiet_end"])
        row = self.notifications.get_preference(user_id)
        if row is None:
            row = NotificationPreference(user_id=user_id)
            self.notifications.add(row)
        row.email_enabled = bool(payload["email_enabled"])
        row.push_enabled = bool(payload["push_enabled"])
        row.quiet_start = quiet_start
        row.quiet_end = quiet_end
        row.types = json.dumps(types, ensure_ascii=False, sort_keys=True)
        row.updated_at = self.clock.now_utc()
        self.notifications.commit()
        return self.get_preferences(user_id)

    def public_key(self) -> str:
        key = (current_app.config.get("VAPID_PUBLIC_KEY") or "").strip()
        if not key:
            raise NotificationError(
                "As notificações push não estão configuradas neste servidor.",
                503,
                "PUSH_NOT_CONFIGURED",
            )
        return key

    def save_subscription(
        self, user_id: int, endpoint: str, p256dh: str, auth: str, user_agent: str | None
    ) -> dict:
        if not endpoint or not p256dh or not auth:
            raise NotificationError("Inscrição de push incompleta.", 400, "VALIDATION_ERROR")
        row = self.notifications.get_subscription_by_endpoint(endpoint)
        if row is None:
            row = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=(user_agent or "")[:255] or None,
                created_at=self.clock.now_utc(),
            )
            self.notifications.add(row)
        else:
            row.user_id = user_id
            row.p256dh = p256dh
            row.auth = auth
            row.user_agent = (user_agent or "")[:255] or None
        self.notifications.commit()
        return row.to_dict()

    def delete_subscription(self, user_id: int, endpoint: str) -> None:
        row = self.notifications.get_subscription_by_endpoint(endpoint or "")
        if row is None or row.user_id != user_id:
            raise NotificationError("Inscrição não encontrada.", 404, "SUBSCRIPTION_NOT_FOUND")
        self.notifications.delete(row)
        self.notifications.commit()

    def send_test(self, user_id: int, channel: str) -> dict:
        self._check_test_channel(user_id, channel)
        self._check_test_rate(user_id)
        status = self._send_test_message(user_id, channel)
        if status != "sent":
            raise NotificationError("Não foi possível enviar o teste.", 502, "NOTIFICATION_FAILED")
        return {"status": "sent", "channel": channel}

    def _check_test_channel(self, user_id, channel):
        if channel not in CHANNELS:
            raise NotificationError("Canal desconhecido.", 400, "VALIDATION_ERROR")
        prefs = self.get_preferences(user_id)
        if channel == "email" and not prefs["email_enabled"]:
            raise NotificationError("Ative o e-mail antes de testar.", 400, "CHANNEL_DISABLED")
        if channel == "push" and not prefs["push_enabled"]:
            raise NotificationError(
                "Ative as notificações push antes de testar.", 400, "CHANNEL_DISABLED"
            )

    def _check_test_rate(self, user_id):
        since = self.clock.now_utc() - timedelta(hours=1)
        limit = self._test_limit()
        if self.notifications.count_tests_since(user_id, since) >= limit:
            raise NotificationError(
                "Você já pediu o máximo de testes desta hora.",
                429,
                "NOTIFICATION_RATE_LIMIT",
            )

    def _test_limit(self):
        raw = current_app.config.get("NOTIFY_TEST_MAX_PER_HOUR")
        if not raw:
            return 3
        return int(raw)

    def _send_test_message(self, user_id, channel):
        user = self.users.get_by_id(user_id)
        today = self.clock.today_local()
        title = "Teste do ProENEM Lab"
        body = "Este é um lembrete de teste."
        if channel == "email":
            status, error = self._deliver_email(
                user,
                title,
                "Este é um lembrete de teste.\n",
                "<p>Este é um lembrete de teste.</p>",
                include_unsubscribe=False,
            )
        else:
            status, error = self._deliver_push(
                user_id, "test", title, body, "/pages/notifications/index.html"
            )
        self._write_log(user_id, "test", channel, today, status, error)
        self.notifications.commit()
        return status

    def list_log(self, user_id: int, limit: int) -> list[NotificationLog]:
        return self.notifications.list_log(user_id, limit)

    def unsubscribe(self, token: str) -> dict:
        data = self._read_token(token)
        kind = data["type"]
        channel = data["channel"]
        user_id = int(data["user_id"])
        if kind not in REMINDER_TYPES or channel not in CHANNELS:
            raise NotificationError("Token inválido.", 400, "INVALID_UNSUBSCRIBE_TOKEN")
        row = self.notifications.get_preference(user_id)
        if row is None:
            row = NotificationPreference(
                user_id=user_id,
                email_enabled=False,
                push_enabled=False,
                quiet_start="22:00",
                quiet_end="07:00",
                updated_at=self.clock.now_utc(),
            )
            self.notifications.add(row)
        types = self._merged_types(row)
        types[kind][channel] = False
        row.types = json.dumps(types, ensure_ascii=False, sort_keys=True)
        row.updated_at = self.clock.now_utc()
        self.notifications.commit()
        return {"type": kind, "channel": channel}

    def is_in_window(self, pref: NotificationPreference, now) -> bool:
        types = self._merged_types(pref)
        max_delay = self._max_delay()
        for kind in TIMED_TYPES:
            slot = types[kind]
            if not self._channels(pref, slot):
                continue
            status = window_status(now, slot["time"], pref.quiet_start, pref.quiet_end, max_delay)
            if status in {"due", "quiet"}:
                return True
        if self._channels(pref, types["study_block"]) and self._block_reminders(pref.user_id, now):
            return True
        return False

    def dispatch_user(self, pref: NotificationPreference, now) -> int:
        sent = 0
        types = self._merged_types(pref)
        today = now.date()
        for kind in REMINDER_TYPES:
            slot = types[kind]
            for channel in self._channels(pref, slot):
                sent += self._dispatch_one(pref, kind, channel, slot, now, today)
        self.notifications.commit()
        return sent

    def _dispatch_one(self, pref, kind: str, channel: str, slot: dict, now, today) -> int:
        user_id = pref.user_id
        if self.notifications.has_status(user_id, kind, channel, today, "sent"):
            return 0
        if not self._dispatch_allowed(pref, kind, channel, slot, now, today):
            return 0
        if self._defer_for_focus(user_id, kind, channel, today):
            return 0
        if self.notifications.count_sent(user_id, today) >= self._max_per_day():
            return 0
        if self._send(user_id, kind, channel, today) == "sent":
            return 1
        return 0

    def _defer_for_focus(self, user_id, kind, channel, today):
        if channel != "push":
            return False
        if not self.focus.is_in_focus(user_id):
            return False
        self._skip(user_id, kind, channel, today, "deferred_focus")
        return True

    def _dispatch_allowed(self, pref, kind, channel, slot, now, today):
        if kind == "study_block":
            return self._study_block_allowed(pref, kind, channel, now, today)
        return self._timed_allowed(pref, kind, channel, slot, now, today)

    def _study_block_allowed(self, pref, kind, channel, now, today):
        outcome = self._study_block_outcome(pref.user_id, now, pref)
        if outcome is None:
            return False
        if outcome == "quiet":
            self._skip(pref.user_id, kind, channel, today, "skipped_quiet_hours")
            return False
        if outcome is False:
            self._skip(pref.user_id, kind, channel, today, "skipped_condition")
            return False
        return True

    def _timed_allowed(self, pref, kind, channel, slot, now, today):
        status = window_status(
            now, slot["time"], pref.quiet_start, pref.quiet_end, self._max_delay()
        )
        if status in {"early", "late"}:
            return False
        if status == "quiet":
            self._skip(pref.user_id, kind, channel, today, "skipped_quiet_hours")
            return False
        if self._is_due(pref.user_id, kind, today):
            return True
        self._skip(pref.user_id, kind, channel, today, "skipped_condition")
        return False

    def _is_due(self, user_id: int, kind: str, today) -> bool:
        if kind == "daily_goal":
            return self.goals.has_goal(user_id, today) and not self.goals.is_completed(
                user_id, today
            )
        if kind == "reviews_due":
            return self.reviews.count_due(user_id, today) > 0
        if kind == "streak_at_risk":
            return self.streaks.current_length(user_id) >= 1 and not self.streaks.has_activity_on(
                user_id, today
            )
        return False

    def _study_block_outcome(self, user_id: int, now, pref):
        reminders = self._block_reminders(user_id, now)
        if not reminders:
            return None
        start = parse_clock(pref.quiet_start)
        end = parse_clock(pref.quiet_end)
        actionable = [moment for moment in reminders if not in_quiet(moment.time(), start, end)]
        if not actionable:
            return "quiet"
        if self.calendar.open_session(user_id) is not None:
            return False
        return True

    def _block_reminders(self, user_id: int, now) -> list:
        week = self.clock.week_start(now.date())
        lead = int(current_app.config.get("STUDY_BLOCK_REMINDER_MINUTES") or 10)
        max_delay = self._max_delay()
        found = []
        for block in self.calendar.list_blocks(user_id, week):
            if block.day_of_week != now.weekday():
                continue
            moment = reminder_moment(now, block.start_minute, lead)
            elapsed = (now - moment).total_seconds() / 60
            if 0 <= elapsed <= max_delay:
                found.append(moment)
        return found

    def _send(self, user_id: int, kind: str, channel: str, today) -> str:
        user = self.users.get_by_id(user_id)
        count = overdue = 0
        if kind == "reviews_due":
            count = self.reviews.count_due(user_id, today)
            overdue = self.reviews.count_overdue(user_id, today)
        unsubscribe_url = self._unsubscribe_url(user_id, kind, channel)
        base = (current_app.config.get("PUBLIC_BASE_URL") or "").rstrip("/")
        title, body, text, html = render(kind, base, unsubscribe_url, count=count, overdue=overdue)
        if channel == "email":
            status, error = self._deliver_email(user, title, text, html, unsubscribe_url)
        else:
            from services.notifications.catalog import LINKS

            status, error = self._deliver_push(user_id, kind, title, body, LINKS[kind])
        self._write_log(user_id, kind, channel, today, status, error)
        return status

    def _deliver_email(
        self, user, title, text, html, unsubscribe_url=None, *, include_unsubscribe=True
    ):
        if user is None or not user.email:
            return "failed", "usuário sem e-mail"
        headers = None
        if unsubscribe_url and include_unsubscribe:
            headers = {
                "List-Unsubscribe": f"<{unsubscribe_url}>",
                "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            }
        try:
            self.email_sender.send(user.email, title, html, text, headers)
        except Exception as exc:
            logger.exception("Falha ao enviar e-mail para o usuário %s", getattr(user, "id", None))
            return "failed", str(exc)[:500]
        return "sent", None

    def _deliver_push(self, user_id: int, kind: str, title: str, body: str, url: str):
        subscriptions = self.notifications.list_subscriptions(user_id)
        if not subscriptions:
            return "failed", "sem inscrição"
        payload = {"title": title, "body": body, "url": url, "tag": kind}
        delivered = False
        for subscription in list(subscriptions):
            result = self.push_sender.send(subscription, payload)
            if result == "ok":
                delivered = True
                subscription.last_success_at = self.clock.now_utc()
            elif result == "gone":
                self.notifications.delete(subscription)
        if delivered:
            return "sent", None
        return "failed", "push recusado"

    def _skip(self, user_id: int, kind: str, channel: str, today, status: str) -> None:
        if self.notifications.has_status(user_id, kind, channel, today, status):
            return
        self._write_log(user_id, kind, channel, today, status, None)

    def _write_log(self, user_id, kind, channel, today, status, error) -> None:
        row = NotificationLog(
            user_id=user_id,
            type=kind,
            channel=channel,
            local_date=today,
            status=status,
            error=error,
            created_at=self.clock.now_utc(),
        )
        self.notifications.add_log(row)

    def _channels(self, pref: NotificationPreference, slot: dict) -> list[str]:
        found = []
        if pref.email_enabled and slot.get("email"):
            found.append("email")
        if pref.push_enabled and slot.get("push"):
            found.append("push")
        return found

    def _merged_types(self, pref: NotificationPreference) -> dict:
        merged = default_types()
        stored = pref.parsed_types()
        for kind, slot in stored.items():
            if kind not in merged or not isinstance(slot, dict):
                continue
            merged[kind]["email"] = bool(slot.get("email"))
            merged[kind]["push"] = bool(slot.get("push"))
            if "time" in merged[kind] and slot.get("time"):
                merged[kind]["time"] = slot["time"]
        return merged

    def _validate_types(self, raw) -> dict:
        if not isinstance(raw, dict):
            raise NotificationError("Tipos de lembrete inválidos.", 400, "VALIDATION_ERROR")
        unknown = set(raw) - set(REMINDER_TYPES)
        if unknown:
            raise NotificationError("Tipo de lembrete desconhecido.", 400, "VALIDATION_ERROR")
        merged = default_types()
        for kind in TIMED_TYPES:
            if kind not in raw:
                raise NotificationError("Tipo de lembrete ausente.", 400, "VALIDATION_ERROR")
        for kind, slot in raw.items():
            if not isinstance(slot, dict):
                raise NotificationError("Tipo de lembrete inválido.", 400, "VALIDATION_ERROR")
            merged[kind]["email"] = bool(slot.get("email"))
            merged[kind]["push"] = bool(slot.get("push"))
            if kind in TIMED_TYPES:
                merged[kind]["time"] = self._require_clock(slot.get("time"))
        return merged

    def _require_clock(self, value: str) -> str:
        try:
            parsed = parse_clock(value)
        except (TypeError, ValueError) as exc:
            raise NotificationError(
                "Horário inválido. Use HH:MM em passos de 15 minutos.",
                400,
                "VALIDATION_ERROR",
            ) from exc
        return parsed.strftime("%H:%M")

    def _max_delay(self) -> int:
        return int(current_app.config.get("NOTIFY_MAX_DELAY_MINUTES") or 90)

    def _max_per_day(self) -> int:
        return int(current_app.config.get("NOTIFY_MAX_PER_DAY") or 4)

    def _serializer(self) -> URLSafeSerializer:
        return URLSafeSerializer(current_app.config["SECRET_KEY"], salt=_TOKEN_SALT)

    def _unsubscribe_url(self, user_id: int, kind: str, channel: str) -> str:
        token = self._serializer().dumps({"user_id": user_id, "type": kind, "channel": channel})
        base = (current_app.config.get("PUBLIC_BASE_URL") or "http://127.0.0.1:5000").rstrip("/")
        return f"{base}/api/notifications/unsubscribe?token={token}"

    def _read_token(self, token: str) -> dict:
        if not token:
            raise NotificationError("Token inválido.", 400, "INVALID_UNSUBSCRIBE_TOKEN")
        try:
            data = self._serializer().loads(token)
        except BadSignature as exc:
            raise NotificationError("Token inválido.", 400, "INVALID_UNSUBSCRIBE_TOKEN") from exc
        if not isinstance(data, dict) or "user_id" not in data:
            raise NotificationError("Token inválido.", 400, "INVALID_UNSUBSCRIBE_TOKEN")
        return data

def describe_unsubscribe(result: dict) -> tuple[str, str]:
    return LABELS.get(result["type"], result["type"]), LABELS.get(
        result["channel"], result["channel"]
    )
