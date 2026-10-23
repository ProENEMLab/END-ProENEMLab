from models.testimonial import Testimonial
from repositories.base_repository import BaseRepository

class TestimonialRepository(BaseRepository):

    model = Testimonial

    def list_published(self) -> list[Testimonial]:
        return (
            Testimonial.query.filter(
                Testimonial.published.is_(True),
                Testimonial.consent_recorded_at.isnot(None),
            )
            .order_by(Testimonial.created_at.desc())
            .all()
        )
