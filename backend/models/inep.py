from datetime import datetime, timezone

from extensions import db

def utcnow():
    return datetime.now(timezone.utc)

class InepItemParam(db.Model):

    __tablename__ = "inep_item_params"
    __table_args__ = (
        db.UniqueConstraint("year", "booklet_code", "position", name="uq_inep_item_booklet_pos"),
    )

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    area = db.Column(db.String(2), nullable=False, index=True)
    item_code = db.Column(db.String(64), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    booklet_code = db.Column(db.String(32), nullable=False)
    booklet_color = db.Column(db.String(32), nullable=True)
    answer_key = db.Column(db.String(8), nullable=True)
    skill_code = db.Column(db.String(32), nullable=True)
    param_a = db.Column(db.Float, nullable=True)
    param_b = db.Column(db.Float, nullable=True)
    param_c = db.Column(db.Float, nullable=True)
    abandoned = db.Column(db.Boolean, nullable=False, default=False, server_default="0")

class InepDifficultyCutoff(db.Model):

    __tablename__ = "inep_difficulty_cutoffs"

    area = db.Column(db.String(2), primary_key=True)
    easy_max = db.Column(db.Float, nullable=True)
    medium_max = db.Column(db.Float, nullable=True)
    easy_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    medium_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    hard_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    note = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=utcnow, nullable=True)
