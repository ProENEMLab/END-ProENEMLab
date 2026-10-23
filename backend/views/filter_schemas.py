from marshmallow import Schema, fields, validate

class SavedFilterSchema(Schema):

    name = fields.Str(required=True, validate=validate.Length(min=1, max=80))
    payload = fields.Dict(required=True)

class FilterSetOutputSchema:

    def dump(self, item, many: bool = False):
        if many:
            return [row.to_dict() for row in item]
        return item.to_dict()
