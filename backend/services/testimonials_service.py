from datetime import datetime, timezone

from services.exceptions import TestimonialError
from models.testimonial import Testimonial
from repositories.testimonial_repository import TestimonialRepository

class TestimonialsService:

    def __init__(self, testimonial_repository: TestimonialRepository) -> None:
        self.testimonials = testimonial_repository

    def list_published(self) -> list[Testimonial]:
        return self.testimonials.list_published()

    def add_testimonial(
        self,
        display_name: str,
        quote: str,
        result_text: str,
        *,
        avatar_url: str | None = None,
        consent: bool = False,
        publish: bool = False,
    ) -> dict:
        name = _plain(display_name)
        body = _plain(quote)
        result = _plain(result_text)
        if _missing_testimonial(name, body, result):
            raise TestimonialError("name, quote and result are required.", 400, "VALIDATION_ERROR")
        if _publish_without_consent(publish, consent):
            raise TestimonialError(
                "Cannot publish a testimonial without recorded consent.",
                400,
                "CONSENT_REQUIRED",
            )

        now = datetime.now(timezone.utc)
        row = Testimonial(
            display_name=name,
            quote=body,
            result_text=result,
            avatar_url=_avatar(avatar_url),
            consent_recorded_at=_consent_time(now, consent),
            published=_can_publish(publish, consent),
            created_at=now,
        )
        self.testimonials.add(row)
        self.testimonials.commit()
        return {
            "id": row.id,
            "published": row.published,
            "consent_recorded": bool(row.consent_recorded_at),
        }

def _plain(value) -> str:
    if not value:
        return ""
    return str(value).strip()

def _missing_testimonial(name, body, result) -> bool:
    if not name:
        return True
    if not body:
        return True
    if not result:
        return True
    return False

def _publish_without_consent(publish, consent) -> bool:
    if not publish:
        return False
    return not consent

def _avatar(avatar_url):
    text = _plain(avatar_url)
    if not text:
        return None
    return text

def _consent_time(now, consent):
    if consent:
        return now
    return None

def _can_publish(publish, consent) -> bool:
    if not publish:
        return False
    return bool(consent)
