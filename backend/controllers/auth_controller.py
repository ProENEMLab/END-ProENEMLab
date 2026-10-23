from flask import request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.exceptions import AuthError
from services.auth_service import AuthService
from views.auth_schemas import (
    ForgotPasswordSchema,
    LoginSchema,
    RegisterSchema,
    ResetPasswordSchema,
    UserOutputSchema,
)
from views.parsing import parse_json
from views.responses import success, validation_error

FORGOT_MESSAGE = (
    "If the email exists, a reset token was generated. " "Check server logs (Phase 1 simulation)."
)

class AuthController:

    def __init__(self, auth_service: AuthService) -> None:
        self.service = auth_service
        self.register_schema = RegisterSchema()
        self.login_schema = LoginSchema()
        self.forgot_schema = ForgotPasswordSchema()
        self.reset_schema = ResetPasswordSchema()
        self.user_output = UserOutputSchema()

    def register(self):
        try:
            data = parse_json(self.register_schema, request.get_json())
            user = self.service.register_user(data["name"], data["email"], data["password"])
            return success({"user": self.user_output.dump(user)}, 201)
        except ValidationError as err:
            return validation_error(err)

    def login(self):
        try:
            data = parse_json(self.login_schema, request.get_json())
            user, token = self.service.login_user(data["email"], data["password"])
            body = {"access_token": token, "user": self.user_output.dump(user)}
            return success(body, 200)
        except ValidationError as err:
            return validation_error(err)

    def me(self):
        user = self.service.get_user_by_id(current_user_id())
        if not user:
            raise AuthError("User not found.", 404, "USER_NOT_FOUND")
        return success({"user": self.user_output.dump(user)}, 200)

    def forgot_password(self):
        try:
            data = parse_json(self.forgot_schema, request.get_json())
            self.service.forgot_password(data["email"])
            return success({"message": FORGOT_MESSAGE}, 200)
        except ValidationError as err:
            return validation_error(err)

    def reset_password(self):
        try:
            data = parse_json(self.reset_schema, request.get_json())
            user = self.service.reset_password(data["reset_token"], data["new_password"])
            body = {
                "message": "Password updated successfully.",
                "user": self.user_output.dump(user),
            }
            return success(body, 200)
        except ValidationError as err:
            return validation_error(err)

from flask import Blueprint
from flask_jwt_extended import jwt_required

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

def bind_auth_routes() -> None:
    if getattr(bind_auth_routes, "done", False):
        return
    bind_auth_routes.done = True
    from container import auth_controller
    auth_bp.post("/register")(auth_controller.register)
    auth_bp.post("/login")(auth_controller.login)
    auth_bp.get("/me")(jwt_required()(auth_controller.me))
    auth_bp.post("/forgot-password")(auth_controller.forgot_password)
    auth_bp.post("/reset-password")(auth_controller.reset_password)
