from dataclasses import dataclass

@dataclass(frozen=True)
class CalendarLimits:

    slot_minutes: int = 30
    day_start_minute: int = 360
    day_end_minute: int = 1440
    block_min_minutes: int = 30
    block_max_minutes: int = 240
    focus_interval_tolerance_seconds: int = 120
    session_stale_minutes: int = 120

    @classmethod
    def from_config(cls, config) -> "CalendarLimits":
        return cls(
            slot_minutes=int(config.CALENDAR_SLOT_MINUTES),
            day_start_minute=int(config.CALENDAR_DAY_START_MINUTE),
            day_end_minute=int(config.CALENDAR_DAY_END_MINUTE),
            block_min_minutes=int(config.BLOCK_MIN_MINUTES),
            block_max_minutes=int(config.BLOCK_MAX_MINUTES),
            focus_interval_tolerance_seconds=int(config.FOCUS_INTERVAL_TOLERANCE_SECONDS),
            session_stale_minutes=int(config.SESSION_STALE_MINUTES),
        )

def planned_cycles(duration_minutes: int, focus_minutes: int, short_break_minutes: int) -> int:
    span = focus_minutes + short_break_minutes
    if span <= 0:
        return 1
    return max(1, duration_minutes // span)

def ranges_overlap(start: int, duration: int, other_start: int, other_duration: int) -> bool:
    return start < other_start + other_duration and other_start < start + duration

SETTINGS_RANGES = {
    "focus_minutes": (5, 90),
    "short_break_minutes": (1, 30),
    "long_break_minutes": (5, 60),
    "cycles_before_long_break": (2, 8),
}
