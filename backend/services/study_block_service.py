from datetime import date, timedelta

from services.clock import Clock, isoformat_utc
from services.exceptions import CalendarError
from models.study import PomodoroSettings, StudyBlock
from repositories.calendar_repository import CalendarRepository
from services.study_rules import SETTINGS_RANGES, CalendarLimits, planned_cycles, ranges_overlap

class StudyBlockService:

    def __init__(
        self,
        calendar_repository: CalendarRepository,
        clock: Clock,
        limits: CalendarLimits | None = None,
    ) -> None:
        self.calendar = calendar_repository
        self.clock = clock
        self.limits = limits or CalendarLimits()

    def list_subjects(self) -> list[dict]:
        self.calendar.ensure_catalog()
        return [item.to_dict() for item in self.calendar.list_subjects()]

    def week(self, user_id: int, week_start: date) -> dict:
        week_start = self._monday(week_start)
        self.calendar.ensure_catalog()
        settings = self._settings(user_id)
        blocks = self.calendar.list_blocks(user_id, week_start)
        sessions = self.calendar.sessions_for_blocks([block.id for block in blocks])
        past = week_start < self.clock.week_start()
        described = [self._describe(block, settings, sessions, past) for block in blocks]
        return {
            "week_start": week_start.isoformat(),
            "week_end": (week_start + timedelta(days=6)).isoformat(),
            "read_only": past,
            "today": self.clock.today_local().isoformat(),
            "today_start": isoformat_utc(self.clock.start_of_day_utc()),
            "server_now": isoformat_utc(self.clock.now_utc()),
            "grid": {
                "slot_minutes": self.limits.slot_minutes,
                "day_start_minute": self.limits.day_start_minute,
                "day_end_minute": self.limits.day_end_minute,
                "block_min_minutes": self.limits.block_min_minutes,
                "block_max_minutes": self.limits.block_max_minutes,
            },
            "settings": settings.to_dict(),
            "subjects": [item.to_dict() for item in self.calendar.list_subjects()],
            "blocks": described,
            "summary": self._summary(described),
        }

    def create_block(self, user_id: int, payload: dict) -> dict:
        subject = self._subject(payload["subject_id"])
        week = self._monday(payload["week_start"])
        self._ensure_writable(week)
        day = self._day(payload["day_of_week"])
        start = self._geometry(payload["start_minute"], payload["duration_minutes"])
        self._ensure_free(user_id, week, day, start, payload["duration_minutes"])
        now = self.clock.now_utc()
        block = StudyBlock(
            user_id=user_id,
            subject_id=subject.id,
            week_start=week,
            day_of_week=day,
            start_minute=start,
            duration_minutes=payload["duration_minutes"],
            created_at=now,
            updated_at=now,
        )
        self.calendar.add(block)
        self.calendar.commit()
        return self._describe(block, self._settings(user_id), [], False)

    def update_block(self, user_id: int, block_id: int, payload: dict) -> dict:
        block = self._owned(user_id, block_id)
        week = block.week_start
        if payload.get("week_start") is not None:
            week = self._monday(payload["week_start"])
        if week < self.clock.week_start():
            raise CalendarError("Past weeks are read-only.", 409, "PAST_WEEK")
        if "day_of_week" not in payload:
            day = block.day_of_week
        else:
            day = self._day(payload["day_of_week"])
        start = block.start_minute if "start_minute" not in payload else payload["start_minute"]
        if "duration_minutes" not in payload:
            duration = block.duration_minutes
        else:
            duration = payload["duration_minutes"]
        if "subject_id" not in payload:
            subject_id = block.subject_id
        else:
            subject_id = payload["subject_id"]
        subject = self._subject(subject_id)
        self._geometry(start, duration)
        self._ensure_free(user_id, week, day, start, duration, ignore_id=block.id)
        block.week_start = week
        block.day_of_week = day
        block.start_minute = start
        block.duration_minutes = duration
        block.subject_id = subject.id
        block.updated_at = self.clock.now_utc()
        self.calendar.commit()
        past = week < self.clock.week_start()
        return self._describe(block, self._settings(user_id), [], past)

    def delete_block(self, user_id: int, block_id: int) -> None:
        block = self._owned(user_id, block_id)
        if block.week_start < self.clock.week_start():
            raise CalendarError("Past weeks are read-only.", 409, "PAST_WEEK")
        self.calendar.detach_block(block.id)
        self.calendar.delete(block)
        self.calendar.commit()

    def copy_previous_week(self, user_id: int, week_start: date) -> dict:
        week_start = self._monday(week_start)
        self._ensure_writable(week_start)
        if self.calendar.list_blocks(user_id, week_start):
            raise CalendarError(
                "The destination week already has blocks.",
                409,
                "WEEK_NOT_EMPTY",
            )
        source = self.calendar.list_blocks(user_id, week_start - timedelta(days=7))
        now = self.clock.now_utc()
        for block in source:
            self.calendar.add(
                StudyBlock(
                    user_id=user_id,
                    subject_id=block.subject_id,
                    week_start=week_start,
                    day_of_week=block.day_of_week,
                    start_minute=block.start_minute,
                    duration_minutes=block.duration_minutes,
                    created_at=now,
                    updated_at=now,
                )
            )
        self.calendar.commit()
        return self.week(user_id, week_start)

    def get_settings(self, user_id: int) -> dict:
        settings = self._settings(user_id)
        return self._settings_payload(settings)

    def update_settings(self, user_id: int, payload: dict) -> dict:
        settings = self._settings(user_id)
        for field, (low, high) in SETTINGS_RANGES.items():
            if field not in payload:
                continue
            value = payload[field]
            if value < low or value > high:
                raise CalendarError(f"{field} is out of range.", 400, "VALIDATION_ERROR")
            setattr(settings, field, value)
        if "auto_start_blocks" in payload:
            settings.auto_start_blocks = bool(payload["auto_start_blocks"])
        for flag in ("focus_mode_enabled", "focus_mode_fullscreen", "focus_mode_sound"):
            if flag in payload:
                setattr(settings, flag, bool(payload[flag]))
        settings.updated_at = self.clock.now_utc()
        self.calendar.commit()
        return self._settings_payload(settings)

    def _settings_payload(self, settings: PomodoroSettings) -> dict:
        payload = settings.to_dict()
        payload["server_now"] = isoformat_utc(self.clock.now_utc())
        payload["today"] = self.clock.today_local().isoformat()
        payload["today_start"] = isoformat_utc(self.clock.start_of_day_utc())
        return payload

    def _settings(self, user_id: int) -> PomodoroSettings:
        settings = self.calendar.get_settings(user_id)
        if settings:
            return settings
        settings = PomodoroSettings.create_default(user_id, self.clock.now_utc())
        self.calendar.add(settings)
        self.calendar.commit()
        return settings

    def _describe(
        self, block: StudyBlock, settings: PomodoroSettings, sessions, past: bool
    ) -> dict:
        subject = self.calendar.get_subject(block.subject_id)
        cycles = planned_cycles(
            block.duration_minutes,
            settings.focus_minutes,
            settings.short_break_minutes,
        )
        return {
            "id": block.id,
            "subject_id": block.subject_id,
            "subject": (
                {
                    "id": subject.id,
                    "name": subject.name,
                    "color": subject.color,
                }
                if subject
                else None
            ),
            "week_start": block.week_start.isoformat(),
            "day_of_week": block.day_of_week,
            "start_minute": block.start_minute,
            "duration_minutes": block.duration_minutes,
            "planned_cycles": cycles,
            "outcome": self._outcome(block, sessions, cycles, past),
        }

    def _outcome(self, block, sessions, cycles: int, past: bool) -> str | None:
        if not past:
            return None
        linked = [item for item in sessions if item.block_id == block.id]
        if not linked:
            return "missed"
        if _block_done(linked, cycles):
            return "done"
        if _block_started(linked):
            return "partial"
        return "missed"

    def _summary(self, blocks: list[dict]) -> list[dict]:
        totals: dict[int, dict] = {}
        for block in blocks:
            subject = block["subject"]
            if not subject:
                continue
            row = totals.setdefault(
                subject["id"],
                {
                    "subject_id": subject["id"],
                    "name": subject["name"],
                    "color": subject["color"],
                    "total_planned_minutes": 0,
                },
            )
            row["total_planned_minutes"] += block["duration_minutes"]
        return list(totals.values())

    def _owned(self, user_id: int, block_id: int) -> StudyBlock:
        block = self.calendar.get_by_id(block_id)
        if not block or block.user_id != user_id:
            raise CalendarError("Block not found.", 404, "BLOCK_NOT_FOUND")
        return block

    def _subject(self, subject_id: int):
        subject = self.calendar.get_subject(subject_id)
        if not subject:
            raise CalendarError("Subject not found.", 404, "SUBJECT_NOT_FOUND")
        return subject

    def _monday(self, value: date) -> date:
        if value is None or value.weekday() != 0:
            raise CalendarError("week_start must be a Monday.", 400, "VALIDATION_ERROR")
        return value

    def _day(self, value: int) -> int:
        if value not in range(7):
            raise CalendarError("day_of_week must be 0–6.", 400, "VALIDATION_ERROR")
        return value

    def _geometry(self, start: int, duration: int) -> int:
        slot = self.limits.slot_minutes
        if start % slot != 0:
            raise CalendarError(
                f"start_minute must be a multiple of {slot}.",
                400,
                "VALIDATION_ERROR",
            )
        if duration % slot != 0:
            raise CalendarError(
                f"duration_minutes must be a multiple of {slot}.",
                400,
                "VALIDATION_ERROR",
            )
        if duration < self.limits.block_min_minutes or duration > self.limits.block_max_minutes:
            raise CalendarError("duration_minutes is out of range.", 400, "VALIDATION_ERROR")
        if start < self.limits.day_start_minute or start + duration > self.limits.day_end_minute:
            raise CalendarError("Block is outside the visible day.", 400, "VALIDATION_ERROR")
        return start

    def _ensure_writable(self, week: date) -> None:
        if week < self.clock.week_start():
            raise CalendarError("Past weeks are read-only.", 409, "PAST_WEEK")

    def _ensure_free(
        self,
        user_id: int,
        week: date,
        day: int,
        start: int,
        duration: int,
        ignore_id: int | None = None,
    ) -> None:
        for block in self.calendar.list_blocks(user_id, week):
            if block.id == ignore_id or block.day_of_week != day:
                continue
            if ranges_overlap(start, duration, block.start_minute, block.duration_minutes):
                raise CalendarError(
                    "This block overlaps another one.",
                    409,
                    "OVERLAP",
                    {"conflicting_block_id": block.id},
                )

def _block_done(linked, cycles) -> bool:
    for item in linked:
        if item.status == "completed":
            return True
        done = item.completed_cycles or 0
        if done >= cycles:
            return True
    return False

def _block_started(linked) -> bool:
    for item in linked:
        focused = item.focused_seconds or 0
        if focused > 0:
            return True
        done = item.completed_cycles or 0
        if done > 0:
            return True
    return False
