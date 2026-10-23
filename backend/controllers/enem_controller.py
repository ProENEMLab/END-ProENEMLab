from flask import request

from services.enem_service import EnemService
from views.responses import error_response, success

class EnemController:

    def __init__(self, enem_service: EnemService) -> None:
        self.service = enem_service

    def sync(self):
        try:
            payload = request.get_json(silent=True) or {}
            year = payload.get("year") or payload.get("ano")
            all_years = bool(payload.get("all_years") or payload.get("todas"))
            result = self.service.sync_exams(
                year=int(year) if year else None,
                all_years=all_years,
            )
            return success(result, 200)
        except (TypeError, ValueError):
            return error_response("year inválido.", 400, "VALIDATION_ERROR")
