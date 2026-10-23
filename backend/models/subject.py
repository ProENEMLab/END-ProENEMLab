import re
import unicodedata

from extensions import db
from services.subject_names import DEFAULT_SUBJECT_COLOR, SUBJECT_AREA, SUBJECT_COLOR

def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return text or "disciplina"

class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    area = db.Column(db.String(2), nullable=True)
    color = db.Column(db.String(7), nullable=False, default=DEFAULT_SUBJECT_COLOR)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "area": self.area,
            "color": self.color,
        }

    @classmethod
    def from_name(cls, name: str) -> "Subject":
        cleaned = name.strip()
        return cls(
            name=cleaned,
            slug=slugify(cleaned),
            area=SUBJECT_AREA.get(cleaned),
            color=SUBJECT_COLOR.get(cleaned, DEFAULT_SUBJECT_COLOR),
        )
