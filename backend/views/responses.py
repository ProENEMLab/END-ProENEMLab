from flask import jsonify
from marshmallow import ValidationError

def success(payload: dict, status: int = 200):
    return jsonify(payload), status

def error_response(message, status_code: int = 400, code: str | None = None):
    payload = {"error": message}
    if code:
        payload["code"] = code
    return jsonify(payload), status_code

def validation_error(err: ValidationError, *, with_code: bool = True, as_text: bool = False):
    message = str(err.messages) if as_text else err.messages
    if with_code:
        return error_response(message, 400, "VALIDATION_ERROR")
    return jsonify({"error": message}), 400
