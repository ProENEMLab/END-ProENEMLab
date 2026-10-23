import re
from datetime import datetime, time, timedelta

_HHMM = re.compile(r"^(\d{2}):(\d{2})$")

def parse_clock(value: str) -> time:
    match = _HHMM.fullmatch(value or "")
    if not match:
        raise ValueError(value)
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute not in {0, 15, 30, 45}:
        raise ValueError(value)
    return time(hour, minute)

def in_quiet(moment: time, start: time, end: time) -> bool:
    if start == end:
        return False
    if start < end:
        return start <= moment < end
    return moment >= start or moment < end

def at_today(now: datetime, clock: time) -> datetime:
    return datetime.combine(now.date(), clock, tzinfo=now.tzinfo)

def window_status(
    now: datetime,
    clock_value: str,
    quiet_start: str,
    quiet_end: str,
    max_delay_minutes: int,
) -> str:
    scheduled_time = parse_clock(clock_value)
    scheduled = at_today(now, scheduled_time)
    if in_quiet(scheduled_time, parse_clock(quiet_start), parse_clock(quiet_end)):
        if now >= scheduled:
            return "quiet"
        return "early"
    elapsed = (now - scheduled).total_seconds() / 60
    if elapsed < 0:
        return "early"
    if elapsed > max_delay_minutes:
        return "late"
    return "due"

def reminder_moment(now: datetime, start_minute: int, lead_minutes: int) -> datetime:
    start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo) + timedelta(
        minutes=start_minute
    )
    return start - timedelta(minutes=lead_minutes)
