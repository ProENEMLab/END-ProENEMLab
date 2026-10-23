from datetime import date, datetime, time, timedelta, timezone

from services.clock import Clock, app_timezone, as_utc, isoformat_utc
from services.exceptions import CalendarError
from models.study import FocusInterval, PomodoroSettings, StudySession
from repositories.calendar_repository import CalendarRepository
from services.study_rules import CalendarLimits, planned_cycles

class StudySessionService:

    OPEN = ("running", "paused")

    def __init__(
        self,
        calendar_repository: CalendarRepository,
        clock: Clock,
        limits: CalendarLimits | None = None,
    ) -> None:
        self.calendar = calendar_repository
        self.clock = clock
        self.limits = limits or CalendarLimits()

    def active(self, user_id: int) -> dict | None:
        self._sweep(user_id)
        session = self.calendar.open_session(user_id)
        if not session:
            return None
        return self.present(session)

    def start(self, user_id: int, payload: dict) -> dict:
        self._sweep(user_id)
        current = self.calendar.open_session(user_id)
        if current:
            raise CalendarError(
                "There is already an active session.",
                409,
                "ACTIVE_SESSION",
                {"session_id": current.id},
            )
        settings = self._settings(user_id)
        block = None
        if payload.get("block_id") is not None:
            block = self.calendar.get_by_id(payload["block_id"])
            if not block or block.user_id != user_id:
                raise CalendarError("Block not found.", 404, "BLOCK_NOT_FOUND")
            subject_id = block.subject_id
            cycles = planned_cycles(
                block.duration_minutes,
                settings.focus_minutes,
                settings.short_break_minutes,
            )
        elif payload.get("subject_id") is not None:
            subject = self.calendar.get_subject(payload["subject_id"])
            if not subject:
                raise CalendarError("Subject not found.", 404, "SUBJECT_NOT_FOUND")
            subject_id = subject.id
            cycles = settings.cycles_before_long_break
        else:
            raise CalendarError(
                "subject_id or block_id is required.",
                400,
                "VALIDATION_ERROR",
            )
        now = self.clock.now_utc()
        session = StudySession(
            user_id=user_id,
            subject_id=subject_id,
            block_id=block.id if block else None,
            status="running",
            planned_cycles=cycles,
            completed_cycles=0,
            focused_seconds=0,
            started_at=now,
            ended_at=None,
        )
        self.calendar.add(session)
        self.calendar.flush()
        self._open_interval(session, 1)
        self.calendar.commit()
        return self.present(session)

    def pause(self, user_id: int, session_id: int) -> dict:
        session = self._ready(user_id, session_id)
        interval = self.calendar.open_interval(session.id)
        if session.status != "running" or interval is None:
            raise CalendarError(
                "Pause only applies to a running focus interval.",
                409,
                "INVALID_TRANSITION",
            )
        self._close_interval(session, interval)
        session.status = "paused"
        self.calendar.commit()
        return self.present(session)

    def resume(self, user_id: int, session_id: int) -> dict:
        session = self._ready(user_id, session_id)
        interval = self.calendar.open_interval(session.id)
        same_cycle = session.status == "paused"
        next_cycle = session.status == "running" and interval is None
        if not same_cycle and not next_cycle:
            raise CalendarError(
                "Resume only applies to a paused session or a break between cycles.",
                409,
                "INVALID_TRANSITION",
            )
        self._open_interval(session, (session.completed_cycles or 0) + 1)
        session.status = "running"
        self.calendar.commit()
        return self.present(session)

    def complete_cycle(self, user_id: int, session_id: int) -> dict:
        session = self._ready(user_id, session_id)
        interval = self.calendar.open_interval(session.id)
        if session.status != "running" or interval is None:
            raise CalendarError(
                "Complete the cycle only while focus is running.",
                409,
                "INVALID_TRANSITION",
            )
        self._close_interval(session, interval)
        session.completed_cycles = (session.completed_cycles or 0) + 1
        if session.completed_cycles >= session.planned_cycles:
            session.status = "completed"
            session.ended_at = self.clock.now_utc()
        self.calendar.commit()
        return self.present(session)

    def finish(self, user_id: int, session_id: int) -> dict:
        session = self._ready(user_id, session_id)
        if session.status not in self.OPEN:
            raise CalendarError("This session is already closed.", 409, "INVALID_TRANSITION")
        interval = self.calendar.open_interval(session.id)
        if interval is not None:
            self._close_interval(session, interval)
        session.status = "completed" if (session.completed_cycles or 0) >= 1 else "abandoned"
        session.ended_at = self.clock.now_utc()
        self.calendar.commit()
        return self.present(session)

    def history(self, user_id: int, start: date, end: date) -> list[dict]:
        self._sweep(user_id)
        if end < start:
            raise CalendarError("to must be on or after from.", 400, "VALIDATION_ERROR")
        zone = app_timezone()
        start_utc = datetime.combine(start, time.min, tzinfo=zone).astimezone(timezone.utc)
        end_utc = datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone).astimezone(
            timezone.utc
        )
        return [
            self.present(session)
            for session in self.calendar.sessions_between(user_id, start_utc, end_utc)
        ]

    def present(self, session: StudySession) -> dict:
        subject = self.calendar.get_subject(session.subject_id)
        settings = self._settings(session.user_id)
        interval = self.calendar.open_interval(session.id)
        return {
            "id": session.id,
            "status": session.status,
            "subject": (
                {
                    "id": subject.id,
                    "name": subject.name,
                    "color": subject.color,
                }
                if subject
                else None
            ),
            "block_id": session.block_id,
            "planned_cycles": session.planned_cycles,
            "completed_cycles": session.completed_cycles,
            "current_interval_started_at": isoformat_utc(interval.started_at) if interval else None,
            "focused_seconds": session.focused_seconds or 0,
            "cycle_focused_seconds": self._cycle_focused(session),
            "settings": settings.to_dict(),
            "server_now": isoformat_utc(self.clock.now_utc()),
        }

    def _ready(self, user_id: int, session_id: int) -> StudySession:
        self._sweep(user_id)
        session = self._owned(user_id, session_id)
        if session.status not in self.OPEN:
            raise CalendarError("This session is already closed.", 409, "INVALID_TRANSITION")
        return session

    def _owned(self, user_id: int, session_id: int) -> StudySession:
        session = self.calendar.get_session(session_id)
        if not session or session.user_id != user_id:
            raise CalendarError("Session not found.", 404, "SESSION_NOT_FOUND")
        return session

    def _sweep(self, user_id: int) -> None:
        session = self.calendar.open_session(user_id)
        if not session:
            return
        last = self.calendar.last_event_at(session)
        stale = timedelta(minutes=self.limits.session_stale_minutes)
        if self.clock.now_utc() - last <= stale:
            return
        interval = self.calendar.open_interval(session.id)
        if interval is not None:
            self._close_interval(session, interval)
        session.status = "abandoned"
        session.ended_at = self.clock.now_utc()
        self.calendar.commit()

    def _open_interval(self, session: StudySession, cycle: int) -> FocusInterval:
        interval = FocusInterval(
            session_id=session.id,
            cycle_number=cycle,
            started_at=self.clock.now_utc(),
            ended_at=None,
        )
        self.calendar.add(interval)
        return interval

    def _close_interval(self, session: StudySession, interval: FocusInterval) -> None:
        settings = self._settings(session.user_id)
        started = as_utc(interval.started_at)
        elapsed = int((self.clock.now_utc() - started).total_seconds())
        cap = settings.focus_minutes * 60 + self.limits.focus_interval_tolerance_seconds
        credited = max(0, min(elapsed, cap))
        interval.ended_at = started + timedelta(seconds=credited)
        session.focused_seconds = (session.focused_seconds or 0) + credited

    def _cycle_focused(self, session: StudySession) -> int:
        cycle = (session.completed_cycles or 0) + 1
        total = 0
        for interval in self.calendar.list_intervals(session.id):
            if interval.cycle_number != cycle or interval.ended_at is None:
                continue
            total += int((as_utc(interval.ended_at) - as_utc(interval.started_at)).total_seconds())
        return max(0, total)

    def _settings(self, user_id: int) -> PomodoroSettings:
        settings = self.calendar.get_settings(user_id)
        if settings:
            return settings
        settings = PomodoroSettings.create_default(user_id, self.clock.now_utc())
        self.calendar.add(settings)
        self.calendar.commit()
        return settings
