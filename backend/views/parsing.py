from datetime import datetime

from marshmallow import Schema, ValidationError

def parse_json(schema: Schema, data: dict | None) -> dict:
    return schema.load(data or {})

def parse_date_arg(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError("date must be YYYY-MM-DD.") from exc
