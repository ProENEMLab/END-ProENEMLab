from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class SavedFilterSet(db.Model):
    __tablename__ = "saved_filter_sets"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_saved_filter_user_name"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", back_populates="saved_filter_sets")

    def to_dict(self) -> dict:
        import json

        try:
            payload = json.loads(self.payload_json)
        except json.JSONDecodeError:
            payload = {}
        return {
            "id": self.id,
            "name": self.name,
            "payload": payload if isinstance(payload, dict) else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
