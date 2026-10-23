from marshmallow import Schema, fields, validate

class NoteCreateSchema(Schema):

    content = fields.Str(required=True, validate=validate.Length(min=1))

class NoteUpdateSchema(Schema):

    content = fields.Str(required=True, validate=validate.Length(min=1))

class NoteOutputSchema:

    def dump(self, note, many: bool = False):
        if many:
            return [item.to_dict() for item in note]
        return note.to_dict()
