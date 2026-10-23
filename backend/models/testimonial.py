from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(120), nullable=False)
    avatar_url = db.Column(db.String(512), nullable=True)
    result_text = db.Column(db.String(255), nullable=False)
    quote = db.Column(db.Text, nullable=False)
    consent_recorded_at = db.Column(db.DateTime, nullable=True)
    published = db.Column(db.Boolean, nullable=False, default=False, server_default="0")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "avatar_url": self.avatar_url,
            "result_text": self.result_text,
            "quote": self.quote,
        }
