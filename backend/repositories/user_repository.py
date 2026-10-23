from models.user import User
from repositories.base_repository import BaseRepository

class UserRepository(BaseRepository):

    model = User

    def get_by_email(self, email: str) -> User | None:
        return User.query.filter_by(email=email).first()

    def get_by_reset_token(self, reset_token: str) -> User | None:
        return User.query.filter_by(reset_token=reset_token).first()
