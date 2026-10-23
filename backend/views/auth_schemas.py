from marshmallow import Schema, fields, validate

class RegisterSchema(Schema):

    name = fields.Str(required=True, validate=validate.Length(min=1, max=120))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))

class LoginSchema(Schema):

    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1))

class ForgotPasswordSchema(Schema):

    email = fields.Email(required=True)

class ResetPasswordSchema(Schema):

    reset_token = fields.Str(required=True, validate=validate.Length(min=1))
    new_password = fields.Str(required=True, validate=validate.Length(min=8))

class UserOutputSchema:

    def dump(self, user) -> dict:
        return user.to_dict()
