from services.testimonials_service import TestimonialsService
from views.responses import success
from views.testimonial_schemas import TestimonialOutputSchema

class TestimonialController:

    def __init__(self, testimonials_service: TestimonialsService) -> None:
        self.service = testimonials_service
        self.output = TestimonialOutputSchema()

    def list_testimonials(self):
        items = self.service.list_published()
        return success({"items": self.output.dump(items, many=True)}, 200)

from flask import Blueprint

testimonials_bp = Blueprint("testimonials", __name__)

def bind_testimonial_routes() -> None:
    if getattr(bind_testimonial_routes, "done", False):
        return
    bind_testimonial_routes.done = True
    from container import testimonial_controller
    testimonials_bp.get("/api/testimonials")(testimonial_controller.list_testimonials)
