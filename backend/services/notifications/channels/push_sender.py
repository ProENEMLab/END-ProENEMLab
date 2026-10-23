import json
import logging

from flask import current_app

logger = logging.getLogger(__name__)

class WebPushSender:

    def send(self, subscription, payload: dict) -> str:
        private_key = current_app.config.get("VAPID_PRIVATE_KEY") or ""
        if not private_key:
            logger.error("VAPID_PRIVATE_KEY ausente; push não enviado")
            return "error"
        try:
            from pywebpush import WebPushException, webpush
        except ImportError:
            logger.exception("pywebpush não está instalado")
            return "error"
        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
                },
                data=json.dumps(payload, ensure_ascii=False),
                vapid_private_key=private_key,
                vapid_claims={
                    "sub": current_app.config.get("VAPID_SUBJECT")
                    or "mailto:nao-responda@proenem.lab"
                },
                ttl=60,
            )
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                return "gone"
            logger.warning("Push recusado (%s)", status)
            return "error"
        except Exception:
            logger.exception("Falha ao enviar push")
            return "error"
        return "ok"
