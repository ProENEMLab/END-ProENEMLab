from extensions import db
from models.inep import InepDifficultyCutoff, InepItemParam
from repositories.base_repository import BaseRepository

class InepItemRepository(BaseRepository):

    model = InepItemParam

    def find_slot(self, year: int, booklet_code: str, position: int) -> InepItemParam | None:
        return InepItemParam.query.filter_by(
            year=year, booklet_code=booklet_code, position=position
        ).first()

    def abandoned_codes(self, years: list[int]) -> set[tuple[int, str]]:
        if not years:
            return set()
        rows = InepItemParam.query.filter(
            InepItemParam.year.in_(years),
            InepItemParam.abandoned.is_(True),
        ).all()
        return {(row.year, row.item_code) for row in rows if row.item_code}

    def list_reference_items(self, years: list[int], color: str) -> list[InepItemParam]:
        if not years:
            return []
        return InepItemParam.query.filter(
            InepItemParam.year.in_(years),
            db.func.upper(InepItemParam.booklet_color) == color.upper(),
        ).all()

    def list_all(self) -> list[InepItemParam]:
        return InepItemParam.query.order_by(InepItemParam.id.asc()).all()

    def reference_matches(
        self, year: int, area: str, position: int, color: str
    ) -> list[InepItemParam]:
        return InepItemParam.query.filter(
            InepItemParam.year == year,
            InepItemParam.area == area,
            InepItemParam.position == position,
            db.func.upper(InepItemParam.booklet_color) == color.upper(),
        ).all()

    def list_cutoffs(self) -> list[InepDifficultyCutoff]:
        return InepDifficultyCutoff.query.all()

    def get_cutoff(self, area: str) -> InepDifficultyCutoff | None:
        return db.session.get(InepDifficultyCutoff, area)

    def save_cutoff(self, row: InepDifficultyCutoff) -> InepDifficultyCutoff:
        self.add(row)
        return row

    def delete_cutoffs(self) -> None:
        InepDifficultyCutoff.query.delete()
