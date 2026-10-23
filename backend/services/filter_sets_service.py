import json
from datetime import datetime, timezone

from services.exceptions import FilterSetError
from models.saved_filter import SavedFilterSet
from repositories.filter_repository import FilterRepository

class FilterSetsService:

    def __init__(self, filter_repository: FilterRepository) -> None:
        self.filters = filter_repository

    def list_filter_sets(self, user_id: int) -> list[SavedFilterSet]:
        return self.filters.list_by_user(user_id)

    def upsert_filter_set(self, user_id: int, name: str, payload: dict) -> SavedFilterSet:
        name = (name or "").strip()
        if not name:
            raise FilterSetError("name is required.", 400, "VALIDATION_ERROR")
        if len(name) > 80:
            raise FilterSetError("name must be at most 80 characters.", 400, "VALIDATION_ERROR")

        normalized = self.normalize_payload(payload)
        encoded = json.dumps(normalized, ensure_ascii=False)
        row = self.filters.get_by_name(user_id, name)
        now = datetime.now(timezone.utc)
        if row:
            row.payload_json = encoded
            row.updated_at = now
        else:
            row = SavedFilterSet(
                user_id=user_id,
                name=name,
                payload_json=encoded,
                created_at=now,
                updated_at=now,
            )
            self.filters.add(row)
        self.filters.commit()
        return row

    def delete_filter_set(self, user_id: int, filter_set_id: int) -> None:
        row = self.filters.get_by_id(filter_set_id)
        if not row or row.user_id != user_id:
            raise FilterSetError("Filter set not found.", 404, "FILTER_SET_NOT_FOUND")
        self.filters.delete(row)
        self.filters.commit()

    def normalize_payload(self, payload: dict | None) -> dict:
        if not isinstance(payload, dict):
            raise FilterSetError("payload must be an object.", 400, "VALIDATION_ERROR")
        return {
            "years": self._ints(payload, "years"),
            "subjects": self._strs(payload, "subjects"),
            "topic_ids": self._ints(payload, "topic_ids"),
            "languages": self._strs(payload, "languages"),
            "exclude_answered": bool(payload.get("exclude_answered")),
        }

    def _ints(self, payload: dict, key: str) -> list[int]:
        values = payload.get(key) or []
        if not isinstance(values, list):
            raise FilterSetError(f"{key} must be a list.", 400, "VALIDATION_ERROR")
        parsed = []
        for item in values:
            try:
                parsed.append(int(item))
            except (TypeError, ValueError) as exc:
                raise FilterSetError(
                    f"{key} contains a non-integer.",
                    400,
                    "VALIDATION_ERROR",
                ) from exc
        return list(dict.fromkeys(parsed))

    def _strs(self, payload: dict, key: str) -> list[str]:
        values = payload.get(key) or []
        if not isinstance(values, list):
            raise FilterSetError(f"{key} must be a list.", 400, "VALIDATION_ERROR")
        cleaned = [str(item).strip() for item in values if str(item).strip()]
        return list(dict.fromkeys(cleaned))
