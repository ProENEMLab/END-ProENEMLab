from marshmallow import Schema, fields, validate

class GoalCreateSchema(Schema):

    description = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    target_date = fields.Date(required=True, format="%Y-%m-%d")

class GoalOutputSchema:

    def dump(self, goal, many: bool = False):
        if many:
            return [item.to_dict() for item in goal]
        return goal.to_dict()
