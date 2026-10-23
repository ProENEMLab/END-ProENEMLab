from datetime import date, datetime, timedelta

from services.clock import Clock, as_utc
from services.exceptions import ApiError
from repositories.calendar_repository import CalendarRepository
from repositories.insight_repository import ReportRepository
from repositories.learning_repository import ReviewRepository

class WeeklyReportService:

    def __init__(
        self,
        report_repository: ReportRepository,
        calendar_repository: CalendarRepository,
        review_repository: ReviewRepository,
        clock: Clock,
        min_answers: int = 5,
        delta_pp: int = 10,
    ) -> None:
        self.reports = report_repository
        self.calendar = calendar_repository
        self.reviews = review_repository
        self.clock = clock
        self.min_answers = min_answers
        self.delta_pp = delta_pp

    def weekly(self, user_id: int, week_start: date | None = None) -> dict:
        current = self.clock.week_start()
        start = current if week_start is None else week_start
        self._ensure_selectable(start, current)
        if start < current:
            stored = self.reports.get_payload(user_id, start)
            if stored is not None:
                return stored
            payload = self._build(user_id, start, partial=False)
            return self.reports.save_payload(user_id, start, payload, self.clock.now_utc())
        return self._build(user_id, start, partial=True)

    def history(self, user_id: int, limit: int = 8) -> dict:
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 52:
            raise ApiError("limit fica entre 1 e 52.", 400, "VALIDATION_ERROR")
        current = self.clock.week_start()
        weeks = []
        for offset in range(limit - 1, -1, -1):
            payload = self.weekly(user_id, current - timedelta(days=7 * offset))
            weeks.append(
                {
                    "week_start": payload["week_start"],
                    "net_seconds": payload["net_study"]["total_seconds"],
                    "evolved_count": len(payload["topics"]["evolved"]),
                    "regressed_count": len(payload["topics"]["regressed"]),
                }
            )
        return {"weeks": weeks}

    def rebuild(self, user_id: int, week_start: date) -> dict:
        current = self.clock.week_start()
        self._ensure_selectable(week_start, current)
        if week_start >= current:
            raise ApiError(
                "A semana atual é calculada na hora e não é gravada.",
                400,
                "WEEK_IS_OPEN",
            )
        payload = self._build(user_id, week_start, partial=False)
        return self.reports.replace_payload(user_id, week_start, payload, self.clock.now_utc())

    def _ensure_selectable(self, week_start: date, current: date) -> None:
        if week_start.weekday() != 0:
            raise ApiError("week_start tem que ser uma segunda-feira.", 400, "WEEK_NOT_MONDAY")
        if week_start > current:
            raise ApiError("Semana futura ainda não existe.", 400, "FUTURE_WEEK")

    def _build(self, user_id: int, week_start: date, *, partial: bool) -> dict:
        start, end = self.clock.week_bounds_utc(week_start)
        previous_start = week_start - timedelta(days=7)
        current_rows = self.reports.topic_stats(user_id, start, end)
        previous_rows = self.reports.topic_stats(
            user_id, *self.clock.week_bounds_utc(previous_start)
        )
        before_rows = self.reports.topic_stats_before(user_id, start)
        answers, correct = self.reports.attempt_totals(user_id, start, end)
        topics = self._classify(
            current_rows,
            previous_rows,
            before_rows,
            self.reviews.due_counts_by_topic(user_id, self.clock.today_local()),
        )
        net = self._net_study(user_id, week_start, start, end)
        return {
            "week_start": week_start.isoformat(),
            "week_end": (week_start + timedelta(days=6)).isoformat(),
            "is_partial": partial,
            "net_study": net,
            "topics": topics,
            "totals": {
                "answers": answers,
                "accuracy": _rate(correct, answers),
            },
            "focus_interruptions": self.calendar.interruption_count(user_id, start, end),
        }

    def _net_study(self, user_id: int, week_start: date, start: datetime, end: datetime) -> dict:
        intervals = self.calendar.closed_focus_overlapping(user_id, start, end)
        by_day = []
        by_subject: dict[int, dict] = {}
        total = 0
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            day_start = self.clock.start_of_day_utc(day)
            day_end = self.clock.start_of_day_utc(day + timedelta(days=1))
            seconds = 0
            for interval in intervals:
                piece = _overlap_seconds(
                    interval["started_at"], interval["ended_at"], day_start, day_end
                )
                if piece <= 0:
                    continue
                seconds += piece
                bucket = by_subject.setdefault(
                    interval["subject_id"],
                    {
                        "subject_id": interval["subject_id"],
                        "name": interval["name"],
                        "seconds": 0,
                    },
                )
                bucket["seconds"] += piece
            total += seconds
            by_day.append({"date": day.isoformat(), "seconds": seconds})
        previous = week_start - timedelta(days=7)
        stored = self.reports.get_payload(user_id, previous)
        if stored is not None:
            previous_seconds = int(stored["net_study"]["total_seconds"])
        else:
            previous_bounds = self.clock.week_bounds_utc(previous)
            previous_seconds = _seconds_in_window(
                self.calendar.closed_focus_overlapping(user_id, *previous_bounds),
                *previous_bounds,
            )
        subjects = sorted(by_subject.values(), key=lambda row: (-row["seconds"], row["name"]))
        return {
            "total_seconds": total,
            "previous_week_seconds": previous_seconds,
            "planned_seconds": self.calendar.planned_seconds(user_id, week_start),
            "by_subject": subjects,
            "by_day": by_day,
        }

    def _classify(self, current_rows, previous_rows, before_rows, due_by_topic) -> dict:
        previous = {row["topic_id"]: row for row in previous_rows}
        before = {row["topic_id"]: row for row in before_rows}
        buckets = {
            "evolved": [],
            "regressed": [],
            "stable": [],
            "new": [],
            "insufficient_data": [],
        }
        for row in current_rows:
            self._place_row(buckets, row, previous, before, due_by_topic)
        _sort_insight_buckets(buckets)
        return buckets

    def _place_row(self, buckets, row, previous, before, due_by_topic):
        if row["answers"] < self.min_answers:
            buckets["insufficient_data"].append(_short(row))
            return
        kind, item = self._compared_item(row, previous, before)
        if kind == "new":
            buckets["new"].append(item)
            return
        if kind == "insufficient_data":
            buckets["insufficient_data"].append(item)
            return
        self._store_compared(buckets, row, item, due_by_topic)

    def _compared_item(self, row, previous, before):
        prior = before.get(row["topic_id"])
        earlier = previous.get(row["topic_id"])
        prior_answers = prior["answers"] if prior else 0
        earlier_answers = earlier["answers"] if earlier else 0
        if prior_answers == 0 and earlier_answers == 0:
            return "new", _fresh(row)
        if earlier_answers >= self.min_answers:
            return "compared", _compared(row, earlier, "previous_week")
        if prior_answers >= self.min_answers:
            return "compared", _compared(row, prior, "cumulative")
        return "insufficient_data", _short(row)

    def _store_compared(self, buckets, row, item, due_by_topic):
        if item["delta_pp"] >= self.delta_pp:
            buckets["evolved"].append(item)
            return
        if item["delta_pp"] <= -self.delta_pp:
            item["actions"] = _actions(row["topic_id"], due_by_topic.get(row["topic_id"], 0))
            buckets["regressed"].append(item)
            return
        buckets["stable"].append(item)

def _sort_insight_buckets(buckets):
    buckets["evolved"].sort(key=lambda item: (-item["delta_pp"], -item["answers"], item["name"]))
    buckets["regressed"].sort(key=lambda item: (item["delta_pp"], -item["answers"], item["name"]))
    buckets["stable"].sort(key=lambda item: item["name"])
    buckets["new"].sort(key=lambda item: (-item["answers"], item["name"]))
    buckets["insufficient_data"].sort(key=lambda item: (item["answers"], item["name"]))

def _overlap_seconds(start, end, window_start, window_end) -> int:
    begin = max(as_utc(start), as_utc(window_start))
    finish = min(as_utc(end), as_utc(window_end))
    if finish <= begin:
        return 0
    return int(round((finish - begin).total_seconds()))

def _seconds_in_window(intervals: list[dict], start, end) -> int:
    return sum(
        _overlap_seconds(interval["started_at"], interval["ended_at"], start, end)
        for interval in intervals
        if interval.get("ended_at") is not None
    )

def _rate(correct: int, answers: int) -> float:
    if answers <= 0:
        return 0.0
    return round(correct / answers, 2)

def _delta_pp(accuracy: float, previous: float) -> int:
    return int(round(accuracy * 100) - round(previous * 100))

def _compared(row: dict, base: dict, baseline: str) -> dict:
    accuracy = _rate(row["correct"], row["answers"])
    previous = _rate(base["correct"], base["answers"])
    return {
        "topic_id": row["topic_id"],
        "name": row["name"],
        "subject": row["subject"],
        "accuracy": accuracy,
        "previous_accuracy": previous,
        "delta_pp": _delta_pp(accuracy, previous),
        "answers": row["answers"],
        "baseline": baseline,
    }

def _fresh(row: dict) -> dict:
    return {
        "topic_id": row["topic_id"],
        "name": row["name"],
        "subject": row["subject"],
        "accuracy": _rate(row["correct"], row["answers"]),
        "answers": row["answers"],
    }

def _short(row: dict) -> dict:
    return {"topic_id": row["topic_id"], "name": row["name"], "answers": row["answers"]}

def _actions(topic_id: int, due_count: int) -> list[dict]:
    actions = [{"type": "practice_topic", "topic_id": topic_id}]
    if due_count > 0:
        actions.append({"type": "review_due", "count": int(due_count)})
    return actions
