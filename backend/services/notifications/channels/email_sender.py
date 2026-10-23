import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from flask import current_app

logger = logging.getLogger(__name__)

def build_message(
    to: str, subject: str, html: str, text: str, headers: dict | None
) -> EmailMessage:
    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = current_app.config.get("MAIL_DEFAULT_SENDER") or "nao-responda@proenem.lab"
    email["To"] = to
    for key, value in (headers or {}).items():
        email[key] = value
    email.set_content(text)
    email.add_alternative(html, subtype="html")
    return email

class ConsoleEmailSender:

    def __init__(self, instance_path: str) -> None:
        self.folder = Path(instance_path) / "outbox"

    def send(
        self, to: str, subject: str, html: str, text: str, headers: dict | None = None
    ) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        message = build_message(to, subject, html, text, headers)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = self.folder / f"{stamp}.eml"
        path.write_bytes(message.as_bytes())
        logger.info("E-mail de desenvolvimento gravado em %s", path)

class SmtpEmailSender:

    def send(
        self, to: str, subject: str, html: str, text: str, headers: dict | None = None
    ) -> None:
        host = current_app.config.get("MAIL_SERVER") or ""
        if not host:
            raise OSError("MAIL_SERVER vazio")
        message = build_message(to, subject, html, text, headers)
        port = int(current_app.config.get("MAIL_PORT") or 587)
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            if current_app.config.get("MAIL_USE_TLS", True):
                smtp.starttls()
            user = current_app.config.get("MAIL_USERNAME") or ""
            password = current_app.config.get("MAIL_PASSWORD") or ""
            if user:
                smtp.login(user, password)
            smtp.send_message(message)

class RoutingEmailSender:

    def send(
        self, to: str, subject: str, html: str, text: str, headers: dict | None = None
    ) -> None:
        backend = (current_app.config.get("MAIL_BACKEND") or "console").lower()
        if backend == "console":
            ConsoleEmailSender(current_app.instance_path).send(to, subject, html, text, headers)
            return
        SmtpEmailSender().send(to, subject, html, text, headers)
