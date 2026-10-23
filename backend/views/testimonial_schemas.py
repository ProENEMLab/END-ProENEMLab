class TestimonialOutputSchema:

    def dump(self, item, many: bool = False):
        if many:
            return [row.to_public_dict() for row in item]
        return item.to_public_dict()
