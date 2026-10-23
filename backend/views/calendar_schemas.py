from marshmallow import Schema, fields, validate

class BlockCreateSchema(Schema):

    subject_id = fields.Int(required=True)
    week_start = fields.Date(required=True, format="%Y-%m-%d")
    day_of_week = fields.Int(required=True, validate=validate.Range(min=0, max=6))
    start_minute = fields.Int(required=True)
    duration_minutes = fields.Int(required=True)

class BlockUpdateSchema(Schema):

    subject_id = fields.Int()
    week_start = fields.Date(format="%Y-%m-%d", allow_none=True)
    day_of_week = fields.Int(validate=validate.Range(min=0, max=6))
    start_minute = fields.Int()
    duration_minutes = fields.Int()

class PomodoroSettingsSchema(Schema):

    focus_minutes = fields.Int(required=True, validate=validate.Range(min=5, max=90))
    short_break_minutes = fields.Int(required=True, validate=validate.Range(min=1, max=30))
    long_break_minutes = fields.Int(required=True, validate=validate.Range(min=5, max=60))
    cycles_before_long_break = fields.Int(required=True, validate=validate.Range(min=2, max=8))
    auto_start_blocks = fields.Bool(required=True)
    focus_mode_enabled = fields.Bool()
    focus_mode_fullscreen = fields.Bool()
    focus_mode_sound = fields.Bool()

class InterruptionSchema(Schema):

    kind = fields.Str(
        required=True,
        validate=validate.OneOf(["fullscreen_exit", "tab_hidden"]),
    )
    occurred_at = fields.DateTime(required=True)
    duration_seconds = fields.Int(
        load_default=None,
        allow_none=True,
        validate=validate.Range(min=0),
    )

class SessionStartSchema(Schema):

    subject_id = fields.Int(load_default=None, allow_none=True)
    block_id = fields.Int(load_default=None, allow_none=True)
