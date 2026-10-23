from datetime import timedelta

from services.clock import Clock, as_utc, isoformat_utc
from services.exceptions import CalendarError
from models.study import FocusInterruption
from repositories.calendar_repository import CalendarRepository

class FocusService:

    def __init__(self, calendar_repository: CalendarRepository, clock: Clock) -> None:
        self.calendar = calendar_repository
        self.clock = clock

    def is_in_focus(self, user_id: int) -> bool:
        session = self.calendar.open_session(user_id)
        if session is None or session.status != "running":
            return False
        return self.calendar.open_interval(session.id) is not None

    def status(self, user_id: int) -> dict:
        if not self.is_in_focus(user_id):
            return {"in_focus": False, "session_id": None, "until": None}
        session = self.calendar.open_session(user_id)
        interval = self.calendar.open_interval(session.id)
        settings = self.calendar.get_settings(user_id)
        minutes = settings.focus_minutes if settings else 25
        spent = 0
        for item in self.calendar.list_intervals(session.id):
            if item.cycle_number != interval.cycle_number or item.ended_at is None:
                continue
            spent += int((as_utc(item.ended_at) - as_utc(item.started_at)).total_seconds())
        remaining = max(0, minutes * 60 - spent)
        until = as_utc(interval.started_at) + timedelta(seconds=remaining)
        return {
            "in_focus": True,
            "session_id": session.id,
            "until": isoformat_utc(until),
        }

    def record_interruption(self, user_id: int, session_id: int, payload: dict) -> dict:
        session = self.calendar.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise CalendarError("Session not found.", 404, "SESSION_NOT_FOUND")
        if session.status != "running":
            raise CalendarError(
                "Interruptions apply only to a running session.",
                409,
                "INVALID_TRANSITION",
            )
        row = FocusInterruption(
            session_id=session.id,
            kind=payload["kind"],
            occurred_at=as_utc(payload["occurred_at"]),
            duration_seconds=payload.get("duration_seconds"),
        )
        self.calendar.add(row)
        self.calendar.commit()
        return {
            "id": row.id,
            "session_id": row.session_id,
            "kind": row.kind,
            "occurred_at": isoformat_utc(row.occurred_at),
            "duration_seconds": row.duration_seconds,
        }
