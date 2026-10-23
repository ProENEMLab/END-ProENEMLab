from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

def app_timezone() -> ZoneInfo:
    name = "America/Sao_Paulo"
    if has_app_context():
        name = current_app.config.get("APP_TIMEZONE", name)
    return ZoneInfo(name)

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

class Clock:

    def now_utc(self) -> datetime:
        if has_app_context():
            frozen = current_app.config.get("CLOCK_NOW")
            if frozen is not None:
                return as_utc(frozen)
        return datetime.now(timezone.utc)

    def now_local(self) -> datetime:
        return self.now_utc().astimezone(app_timezone())

    def today_local(self) -> date:
        return self.now_local().date()

    def week_start(self, day: date | None = None) -> date:
        day = day or self.today_local()
        return day - timedelta(days=day.weekday())

    def week_bounds_utc(self, day: date | None = None) -> tuple[datetime, datetime]:
        start = datetime.combine(self.week_start(day), time.min, tzinfo=app_timezone())
        end = start + timedelta(days=7)
        return start.astimezone(timezone.utc), end.astimezone(timezone.utc)

    def start_of_day_utc(self, day: date | None = None) -> datetime:
        day = day or self.today_local()
        start = datetime.combine(day, time.min, tzinfo=app_timezone())
        return start.astimezone(timezone.utc)

def isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return as_utc(value).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
