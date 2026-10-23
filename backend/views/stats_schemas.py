from marshmallow import Schema, fields, validate

class ErrorTypeSchema(Schema):

    error_type = fields.Str(
        required=True,
        validate=validate.OneOf(["conceito", "atencao"]),
    )
