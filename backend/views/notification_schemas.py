from marshmallow import Schema, fields, validate

class PreferencesSchema(Schema):

    email_enabled = fields.Bool(required=True)
    push_enabled = fields.Bool(required=True)
    quiet_start = fields.Str(required=True)
    quiet_end = fields.Str(required=True)
    types = fields.Raw(required=True)

class PushKeySchema(Schema):

    p256dh = fields.Str(required=True)
    auth = fields.Str(required=True)

class SubscriptionSchema(Schema):

    endpoint = fields.Str(required=True)
    keys = fields.Nested(PushKeySchema, required=True)

class EndpointSchema(Schema):

    endpoint = fields.Str(required=True)

class TestSchema(Schema):

    channel = fields.Str(required=True, validate=validate.OneOf(["email", "push"]))
