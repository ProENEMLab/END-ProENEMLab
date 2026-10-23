from flask import Flask, jsonify

from services.exceptions import ApiError

def register_error_handlers(app: Flask) -> None:

    @app.errorhandler(ApiError)
    def handle_api_error(err: ApiError):
        payload = {"error": err.message}
        if err.code:
            payload["code"] = err.code
        for key, value in getattr(err, "extra", {}).items():
            if key not in payload:
                payload[key] = value
        return jsonify(payload), err.status_code
