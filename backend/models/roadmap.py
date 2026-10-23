import json
from datetime import datetime, timezone

from sqlalchemy import text

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class RoadmapVersion(db.Model):

    __tablename__ = "roadmap_versions"
    __table_args__ = (
        db.Index(
            "uq_roadmap_versions_one_active",
            "status",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    reference_year = db.Column(db.Integer, nullable=False)
    editions = db.Column(db.Text, nullable=False)
    edital = db.Column(db.String(255), nullable=False)
    matrix_reference = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(16), nullable=False, default="draft")
    coverage = db.Column(db.Text, nullable=False, default="{}")
    generated_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    activated_at = db.Column(db.DateTime, nullable=True)

    def edition_list(self) -> list[int]:
        return [int(item) for item in json.loads(self.editions or "[]")]

    def coverage_map(self) -> dict[int, float]:
        raw = json.loads(self.coverage or "{}")
        return {int(key): float(value) for key, value in raw.items()}

    def to_summary(self) -> dict:
        return {
            "reference_year": self.reference_year,
            "editions": self.edition_list(),
            "edital": self.edital,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
        }

class RoadmapVersionTopic(db.Model):

    __tablename__ = "roadmap_version_topics"

    version_id = db.Column(db.Integer, db.ForeignKey("roadmap_versions.id"), primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey("topics.id"), primary_key=True)
    position = db.Column(db.Integer, nullable=False)
    incidence_count = db.Column(db.Integer, nullable=False, default=0)
    incidence_weight = db.Column(db.Float, nullable=False, default=0)
    low_incidence = db.Column(db.Boolean, nullable=False, default=False)
    rank_reason = db.Column(db.String(400), nullable=False, default="")

class UserNotice(db.Model):

    __tablename__ = "user_notices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    kind = db.Column(db.String(32), nullable=False)
    payload = db.Column(db.Text, nullable=False, default="{}")
    seen_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        try:
            payload = json.loads(self.payload or "{}")
        except json.JSONDecodeError:
            payload = {"message": self.payload}
        return {
            "id": self.id,
            "kind": self.kind,
            "payload": payload,
            "seen_at": self.seen_at.isoformat() if self.seen_at else None,
        }
