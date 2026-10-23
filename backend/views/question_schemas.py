from marshmallow import Schema, ValidationError, fields, validates

class AnswerSchema(Schema):

    selected_option = fields.Str(required=True)

    @validates("selected_option")
    def validate_option(self, value, **kwargs):
        letter = (value or "").strip().upper()
        if letter not in {"A", "B", "C", "D", "E"}:
            raise ValidationError("selected_option must be one of A–E.")

class QuestionPublicSchema:

    def dump(self, question) -> dict:
        return question.to_public_dict()

class QuestionListSchema:

    def dump(self, payload: dict) -> dict:
        if "items" not in payload:
            return payload
        body = dict(payload)
        body["items"] = [question.to_list_dict() for question in payload["items"]]
        return body

class AttemptOutputSchema:

    def dump(self, attempt, many: bool = False):
        if many:
            return [item.to_dict() for item in attempt]
        return attempt.to_dict()
