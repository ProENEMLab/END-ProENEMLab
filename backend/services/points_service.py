from services.exceptions import PointsError
from models.engagement import POINT_REASONS, POINT_VALUES, PointsTransaction
from repositories.points_repository import PointsRepository
from repositories.user_repository import UserRepository

class PointsService:

    def __init__(
        self,
        points_repository: PointsRepository,
        user_repository: UserRepository,
    ) -> None:
        self.points = points_repository
        self.users = user_repository

    def award_points(
        self,
        user_id: int,
        reason: str,
        amount: int | None = None,
        reference_id: int | None = None,
        *,
        commit: bool = True,
    ) -> PointsTransaction:
        points = self._amount_for(reason, amount)
        user = self._require_user(user_id)
        transaction = PointsTransaction(
            user_id=user_id,
            points=points,
            reason=reason,
            reference_id=reference_id,
        )
        user.total_points = (user.total_points or 0) + points
        self.points.add(transaction)
        if commit:
            self.points.commit()
        return transaction

    def _amount_for(self, reason: str, amount: int | None) -> int:
        if reason not in POINT_REASONS:
            raise PointsError(f"Invalid points reason: {reason}.", 400, "INVALID_POINTS_REASON")
        points = amount if amount is not None else POINT_VALUES[reason]
        if points <= 0:
            raise PointsError("Points amount must be positive.", 400, "INVALID_POINTS_AMOUNT")
        return points

    def _require_user(self, user_id: int):
        user = self.users.get_by_id(user_id)
        if not user:
            raise PointsError("User not found.", 404, "USER_NOT_FOUND")
        return user

    def get_total_points(self, user_id: int) -> int:
        user = self._require_user(user_id)
        return user.total_points or 0

    def list_points_history(self, user_id: int, page: int = 1, per_page: int = 20) -> dict:
        self._require_user(user_id)
        page = max(page, 1)
        per_page = min(max(per_page, 1), 100)
        pagination = self.points.paginate_by_user(user_id, page, per_page)
        return {
            "items": pagination.items,
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "pages": pagination.pages,
        }
