from models.engagement import PointsTransaction
from repositories.base_repository import BaseRepository

class PointsRepository(BaseRepository):

    model = PointsTransaction

    def paginate_by_user(self, user_id: int, page: int, per_page: int):
        query = PointsTransaction.query.filter_by(user_id=user_id).order_by(
            PointsTransaction.created_at.desc(), PointsTransaction.id.desc()
        )
        return query.paginate(page=page, per_page=per_page, error_out=False)
