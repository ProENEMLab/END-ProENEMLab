from datetime import date, timedelta

from flask import current_app, has_app_context
from sqlalchemy.exc import IntegrityError

from services.clock import Clock, isoformat_utc
from services.exceptions import ReviewError
from models.learning import ReviewCycle, ReviewEvent
from repositories.learning_repository import ReviewRepository

DEFAULT_INTERVALS = (1, 3, 7)

class ReviewService:

    def __init__(self, review_repository: ReviewRepository, clock: Clock) -> None:
        self.reviews = review_repository
        self.clock = clock

    def on_attempt(
        self,
        user_id: int,
        question_id: int,
        is_correct: bool,
        context: str,
        attempt_id: int | None = None,
    ) -> dict | None:
        today = self.clock.today_local()
        cycle = self.reviews.get_active(user_id, question_id)
        if context == "review":
            if not cycle or today < cycle.due_date:
                return None
            if is_correct:
                return self._advance(cycle, attempt_id)
            return self._restart(cycle, today, attempt_id, "wrong")
        if is_correct:
            return None
        if cycle:
            return self._restart(cycle, today, attempt_id, "restarted_outside")
        return self._open(user_id, question_id, today, attempt_id)

    def count_due(self, user_id: int, day: date) -> int:
        return self.reviews.count_due(user_id, day)

    def count_overdue(self, user_id: int, day: date) -> int:
        return self.reviews.count_overdue(user_id, day)

    def today(self, user_id: int) -> dict:
        day = self.clock.today_local()
        items = []
        for cycle in self.reviews.list_due(user_id, day):
            if cycle.question is None:
                self._cancel(cycle, None)
                continue
            items.append(self._item(cycle, day))
        items.sort(
            key=lambda item: (
                0 if item["overdue_days"] else 1,
                item["stage"],
                item["due_date"],
                item["cycle_id"],
            )
        )
        overdue = sum(1 for item in items if item["overdue_days"] > 0)
        return {"count": len(items), "overdue_count": overdue, "items": items}

    def upcoming(self, user_id: int, days: int) -> dict:
        days = min(max(int(days), 1), 30)
        start = self.clock.today_local() + timedelta(days=1)
        counts = {start + timedelta(days=offset): 0 for offset in range(days)}
        end = start + timedelta(days=days - 1)
        for cycle in self.reviews.list_between(user_id, start, end):
            counts[cycle.due_date] = counts.get(cycle.due_date, 0) + 1
        return {
            "days": [{"date": day.isoformat(), "count": counts[day]} for day in counts],
        }

    def badge(self, user_id: int) -> dict:
        return {"due_today": self.count_due(user_id, self.clock.today_local())}

    def detail(self, user_id: int, cycle_id: int) -> dict:
        cycle = self._owned(user_id, cycle_id)
        payload = self._item(cycle, self.clock.today_local())
        payload["question"] = cycle.question.to_public_dict()
        return payload

    def history(self, user_id: int, question_id: int) -> dict:
        cycles = []
        for cycle in self.reviews.list_for_question(user_id, question_id):
            cycles.append(
                {
                    "id": cycle.id,
                    "question_id": cycle.question_id,
                    "status": cycle.status,
                    "anchor_date": cycle.anchor_date.isoformat(),
                    "current_stage": cycle.current_stage,
                    "due_date": cycle.due_date.isoformat() if cycle.due_date else None,
                    "restart_count": cycle.restart_count,
                    "completed_at": isoformat_utc(cycle.completed_at),
                    "events": [
                        {
                            "stage": event.stage,
                            "result": event.result,
                            "attempt_id": event.attempt_id,
                            "occurred_at": isoformat_utc(event.occurred_at),
                        }
                        for event in self.reviews.events_for(cycle.id)
                    ],
                }
            )
        return {"cycles": cycles}

    def require_answerable(self, user_id: int, cycle_id: int) -> ReviewCycle:
        cycle = self._owned(user_id, cycle_id)
        if cycle.status != "active":
            raise ReviewError("Revisão não encontrada.", 404, "REVIEW_NOT_FOUND")
        today = self.clock.today_local()
        if cycle.due_date > today:
            label = f"{cycle.due_date.day:02d}/{cycle.due_date.month:02d}"
            raise ReviewError(f"Esta revisão é para {label}", 409, "REVIEW_NOT_DUE")
        return cycle

    def state(self, cycle: ReviewCycle) -> dict:
        events = self.reviews.events_for(cycle.id)
        stage = events[-1].stage if events else cycle.current_stage
        next_due = cycle.due_date.isoformat() if cycle.status == "active" else None
        return {"stage": stage, "next_due_date": next_due, "status": cycle.status}

    def cancel_for_question(self, question_id: int) -> None:
        for cycle in self.reviews.list_active_by_question(question_id):
            self._cancel(cycle, None)

    def _owned(self, user_id: int, cycle_id: int) -> ReviewCycle:
        cycle = self.reviews.get_by_id(cycle_id)
        if not cycle or cycle.user_id != user_id or cycle.question is None:
            if (
                cycle
                and cycle.user_id == user_id
                and cycle.question is None
                and cycle.status == "active"
            ):
                self._cancel(cycle, None)
            raise ReviewError("Revisão não encontrada.", 404, "REVIEW_NOT_FOUND")
        return cycle

    def _open(self, user_id: int, question_id: int, today: date, attempt_id: int | None) -> dict:
        now = self.clock.now_utc()
        cycle = ReviewCycle(
            user_id=user_id,
            question_id=question_id,
            status="active",
            anchor_date=today,
            current_stage=1,
            due_date=self._due(today, 1),
            restart_count=0,
            created_at=now,
            updated_at=now,
        )
        try:
            self.reviews.add(cycle)
            self.reviews.flush()
        except IntegrityError:
            self.reviews.rollback()
            existing = self.reviews.get_active(user_id, question_id)
            if not existing:
                raise
            return self._restart(existing, today, attempt_id, "restarted_outside")
        self._record(cycle, 1, "wrong", attempt_id)
        self.reviews.commit()
        return self._state_from(cycle, 1)

    def _restart(
        self, cycle: ReviewCycle, today: date, attempt_id: int | None, result: str
    ) -> dict:
        failed = cycle.current_stage
        cycle.anchor_date = today
        cycle.current_stage = 1
        cycle.due_date = self._due(today, 1)
        cycle.restart_count += 1
        cycle.status = "active"
        cycle.completed_at = None
        cycle.updated_at = self.clock.now_utc()
        self._record(cycle, failed, result, attempt_id)
        self.reviews.commit()
        return self._state_from(cycle, failed)

    def _advance(self, cycle: ReviewCycle, attempt_id: int | None) -> dict:
        answered = cycle.current_stage
        intervals = self._intervals()
        now = self.clock.now_utc()
        if answered >= len(intervals):
            cycle.status = "completed"
            cycle.completed_at = now
        else:
            cycle.current_stage = answered + 1
            cycle.due_date = self._due(cycle.anchor_date, cycle.current_stage)
        cycle.updated_at = now
        self._record(cycle, answered, "correct", attempt_id)
        self.reviews.commit()
        return self._state_from(cycle, answered)

    def _cancel(self, cycle: ReviewCycle, attempt_id: int | None) -> None:
        stage = cycle.current_stage
        cycle.status = "cancelled"
        cycle.updated_at = self.clock.now_utc()
        self._record(cycle, stage, "cancelled", attempt_id)
        self.reviews.commit()

    def _record(self, cycle: ReviewCycle, stage: int, result: str, attempt_id: int | None) -> None:
        self.reviews.add_event(
            ReviewEvent(
                cycle_id=cycle.id,
                stage=stage,
                result=result,
                attempt_id=attempt_id,
                occurred_at=self.clock.now_utc(),
            )
        )

    def _due(self, anchor: date, stage: int) -> date:
        intervals = self._intervals()
        index = min(max(stage, 1), len(intervals)) - 1
        return anchor + timedelta(days=intervals[index])

    def _intervals(self) -> tuple[int, ...]:
        if has_app_context():
            values = current_app.config.get("REVIEW_INTERVALS_DAYS")
            if values:
                return tuple(int(value) for value in values)
        return DEFAULT_INTERVALS

    def _item(self, cycle: ReviewCycle, day: date) -> dict:
        question = cycle.question
        topic = question.topic.name if question is not None and question.topic is not None else None
        overdue = max((day - cycle.due_date).days, 0)
        return {
            "cycle_id": cycle.id,
            "question_id": cycle.question_id,
            "topic": topic,
            "subject": question.subject if question is not None else None,
            "stage": cycle.current_stage,
            "total_stages": len(self._intervals()),
            "due_date": cycle.due_date.isoformat(),
            "overdue_days": overdue,
        }

    def _state_from(self, cycle: ReviewCycle, stage: int) -> dict:
        next_due = cycle.due_date.isoformat() if cycle.status == "active" else None
        return {"stage": stage, "next_due_date": next_due, "status": cycle.status}
