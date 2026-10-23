import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from flask_jwt_extended import create_access_token
from sqlalchemy.exc import IntegrityError

from services.exceptions import AuthError
from models.user import User
from repositories.user_repository import UserRepository

class AuthService:

    def __init__(self, user_repository: UserRepository) -> None:
        self.users = user_repository

    def register_user(self, name: str, email: str, password: str) -> User:
        email = email.strip().lower()
        if self.users.get_by_email(email):
            raise AuthError("Email already registered.", 409, "EMAIL_ALREADY_EXISTS")

        user = User(name=name.strip(), email=email, total_points=0)
        user.set_password(password)
        self.users.add(user)
        try:
            self.users.commit()
        except IntegrityError:
            self.users.rollback()
            raise AuthError("Email already registered.", 409, "EMAIL_ALREADY_EXISTS")
        return user

    def login_user(self, email: str, password: str) -> tuple[User, str]:
        email = email.strip().lower()
        user = self.users.get_by_email(email)
        if not user or not user.check_password(password):
            raise AuthError("Invalid email or password.", 401, "INVALID_CREDENTIALS")
        token = create_access_token(identity=str(user.id))
        return user, token

    def get_user_by_id(self, user_id: int) -> User | None:
        return self.users.get_by_id(user_id)

    def forgot_password(self, email: str) -> str | None:
        email = email.strip().lower()
        user = self.users.get_by_email(email)
        if not user:
            return None

        token = secrets.token_urlsafe(32)
        hours = current_app.config.get("RESET_TOKEN_EXPIRES_HOURS", 1)
        user.reset_token = token
        user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)
        self.users.commit()
        print(f"[ProENEM Lab] Password reset token for {user.email}: {token}")
        current_app.logger.info("Password reset token generated for %s", user.email)
        return token

    def reset_password(self, reset_token: str, new_password: str) -> User:
        user = self.users.get_by_reset_token(reset_token)
        if not user or not user.reset_token_expires_at:
            raise AuthError("Invalid or expired reset token.", 400, "INVALID_RESET_TOKEN")

        expires = user.reset_token_expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise AuthError("Invalid or expired reset token.", 400, "INVALID_RESET_TOKEN")

        user.set_password(new_password)
        user.reset_token = None
        user.reset_token_expires_at = None
        self.users.commit()
        return user
