from marshmallow import Schema, fields, validate

class TopicStatusSchema(Schema):

    status = fields.Str(
        required=True,
        validate=validate.OneOf(["in_progress", "completed"]),
    )
