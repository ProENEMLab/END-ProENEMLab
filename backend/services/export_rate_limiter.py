from datetime import datetime, timedelta, timezone

from flask import current_app, has_app_context

from services.exceptions import ExportError

class ExportRateLimiter:

    def __init__(self, max_per_hour: int = 10) -> None:
        self.max_per_hour = max_per_hour
        self._hits: dict[int, list[datetime]] = {}

    def reset(self) -> None:
        self._hits.clear()

    def hit(self, user_id: int, now: datetime) -> None:
        moment = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        window_start = moment - timedelta(hours=1)
        recent = [item for item in self._hits.get(user_id, []) if item > window_start]
        if len(recent) >= self._allowance():
            raise ExportError(
                "Você atingiu o limite de exportações desta hora. Tente novamente mais tarde.",
                429,
                "EXPORT_RATE_LIMIT",
            )
        recent.append(moment)
        self._hits[user_id] = recent

    def _allowance(self) -> int:
        if has_app_context():
            return int(current_app.config.get("EXPORT_PDF_MAX_PER_HOUR", self.max_per_hour))
        return self.max_per_hour
