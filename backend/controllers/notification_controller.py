from flask import Response, request
from marshmallow import ValidationError

from controllers.http import current_user_id
from services.notifications.notification_service import NotificationService, describe_unsubscribe
from services.notifications.templates import unsubscribe_page
from views.notification_schemas import (
    EndpointSchema,
    PreferencesSchema,
    SubscriptionSchema,
    TestSchema,
)
from views.parsing import parse_json
from views.responses import success, validation_error

class NotificationController:

    def __init__(self, notification_service: NotificationService) -> None:
        self.service = notification_service
        self.preferences_schema = PreferencesSchema()
        self.subscription_schema = SubscriptionSchema()
        self.endpoint_schema = EndpointSchema()
        self.test_schema = TestSchema()

    def list_preferences(self):
        return success({"preferences": self.service.get_preferences(current_user_id())}, 200)

    def update_preferences(self):
        try:
            data = parse_json(self.preferences_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        preferences = self.service.update_preferences(current_user_id(), data)
        return success({"preferences": preferences}, 200)

    def public_key(self):
        return success({"public_key": self.service.public_key()}, 200)

    def subscribe(self):
        try:
            data = parse_json(self.subscription_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        saved = self.service.save_subscription(
            current_user_id(),
            data["endpoint"],
            data["keys"]["p256dh"],
            data["keys"]["auth"],
            request.headers.get("User-Agent"),
        )
        return success({"subscription": saved}, 201)

    def unsubscribe_push(self):
        try:
            data = parse_json(self.endpoint_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        self.service.delete_subscription(current_user_id(), data["endpoint"])
        return success({"deleted": True}, 200)

    def send_test(self):
        try:
            data = parse_json(self.test_schema, request.get_json())
        except ValidationError as err:
            return validation_error(err)
        return success(self.service.send_test(current_user_id(), data["channel"]), 200)

    def log(self):
        raw = request.args.get("limit", "20")
        try:
            limit = min(max(int(raw), 1), 50)
        except (TypeError, ValueError):
            limit = 20
        rows = self.service.list_log(current_user_id(), limit)
        return success({"log": [row.to_dict() for row in rows]}, 200)

    def unsubscribe(self):
        token = request.args.get("token") or ""
        if not token and request.is_json:
            token = (request.get_json(silent=True) or {}).get("token") or ""
        result = self.service.unsubscribe(token)
        if request.method == "POST":
            return success(
                {"unsubscribed": True, "type": result["type"], "channel": result["channel"]}, 200
            )
        kind, channel = describe_unsubscribe(result)
        return Response(unsubscribe_page(kind, channel), mimetype="text/html")

from flask import Blueprint
from flask_jwt_extended import jwt_required

notification_bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")

def bind_notification_routes() -> None:
    if getattr(bind_notification_routes, "done", False):
        return
    bind_notification_routes.done = True
    from container import notification_controller
    notification_bp.get("/preferences")(jwt_required()(notification_controller.list_preferences))
    notification_bp.put("/preferences")(jwt_required()(notification_controller.update_preferences))
    notification_bp.get("/push/public-key")(jwt_required()(notification_controller.public_key))
    notification_bp.post("/push/subscriptions")(jwt_required()(notification_controller.subscribe))
    notification_bp.delete("/push/subscriptions")(
        jwt_required()(notification_controller.unsubscribe_push)
    )
    notification_bp.post("/test")(jwt_required()(notification_controller.send_test))
    notification_bp.get("/log")(jwt_required()(notification_controller.log))
    notification_bp.get("/unsubscribe")(notification_controller.unsubscribe)
    notification_bp.post("/unsubscribe")(notification_controller.unsubscribe)
