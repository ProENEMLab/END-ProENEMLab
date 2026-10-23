import os
import sys
from datetime import timedelta

_BACKEND_ROOT = os.path.abspath(os.path.dirname(__file__))

def _secret(name: str, dev_default: str) -> str:
    value = os.getenv(name)
    if value:
        return value
    print(
        f"Aviso: {name} não definida; usando o valor de desenvolvimento.",
        file=sys.stderr,
    )
    return dev_default

class Config:
    SECRET_KEY = _secret("SECRET_KEY", "change-me")
    JWT_SECRET_KEY = _secret("JWT_SECRET_KEY", "change-me-too")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(_BACKEND_ROOT, "proenem.db").replace("\\", "/"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    RESET_TOKEN_EXPIRES_HOURS = 1
    CORS_ORIGINS = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            ",".join(
                [
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                    "http://localhost:5500",
                    "http://127.0.0.1:5500",
                    "http://localhost:8080",
                    "http://127.0.0.1:8080",
                    "http://localhost:5000",
                    "http://127.0.0.1:5000",
                ]
            ),
        ).split(",")
        if o.strip()
    ]
    ENEM_API_BASE = os.getenv("ENEM_API_BASE", "https://api.enem.dev/v1").rstrip("/")
    ENEM_AUTO_SYNC = os.getenv("ENEM_AUTO_SYNC", "false").lower() in {"1", "true", "yes"}
    APP_TIMEZONE = os.getenv("APP_TIMEZONE", "America/Sao_Paulo")
    CALENDAR_SLOT_MINUTES = int(os.getenv("CALENDAR_SLOT_MINUTES", "30"))
    CALENDAR_DAY_START_MINUTE = int(os.getenv("CALENDAR_DAY_START_MINUTE", "360"))
    CALENDAR_DAY_END_MINUTE = int(os.getenv("CALENDAR_DAY_END_MINUTE", "1440"))
    BLOCK_MIN_MINUTES = int(os.getenv("BLOCK_MIN_MINUTES", "30"))
    BLOCK_MAX_MINUTES = int(os.getenv("BLOCK_MAX_MINUTES", "240"))
    FOCUS_INTERVAL_TOLERANCE_SECONDS = int(os.getenv("FOCUS_INTERVAL_TOLERANCE_SECONDS", "120"))
    SESSION_STALE_MINUTES = int(os.getenv("SESSION_STALE_MINUTES", "120"))
    INEP_REFERENCE_COLOR = os.getenv("INEP_REFERENCE_COLOR", "AZUL").strip().upper()
    INEP_ITEMS_DIR = os.getenv(
        "INEP_ITEMS_DIR", os.path.join(_BACKEND_ROOT, "repositories", "data", "inep", "itens")
    )
    DIFFICULTY_EASY_MIN_RATE = float(os.getenv("DIFFICULTY_EASY_MIN_RATE", "0.70"))
    DIFFICULTY_MEDIUM_MIN_RATE = float(os.getenv("DIFFICULTY_MEDIUM_MIN_RATE", "0.40"))
    DIFFICULTY_MIN_PLATFORM_ATTEMPTS = int(os.getenv("DIFFICULTY_MIN_PLATFORM_ATTEMPTS", "30"))
    PROGRESSION_WINDOW = int(os.getenv("PROGRESSION_WINDOW", "10"))
    PROGRESSION_MIN_ATTEMPTS = int(os.getenv("PROGRESSION_MIN_ATTEMPTS", "10"))
    PROGRESSION_UNLOCK_PERCENT = int(os.getenv("PROGRESSION_UNLOCK_PERCENT", "80"))
    PROGRESSION_REINFORCE_PERCENT = int(os.getenv("PROGRESSION_REINFORCE_PERCENT", "50"))
    PROGRESSION_RECENT_DAYS = int(os.getenv("PROGRESSION_RECENT_DAYS", "7"))
    PROGRESSION_JUST_UNLOCKED_SECONDS = int(os.getenv("PROGRESSION_JUST_UNLOCKED_SECONDS", "60"))
    PROGRESSION_LEVEL_NAMES = {
        "easy": "fáceis",
        "medium": "médias",
        "hard": "difíceis",
    }
    PROGRESSION_MESSAGES = {
        "advance": "Você liberou as questões {level_name} de {topic_name}!",
        "keep_practicing": (
            "Faltam {remaining} questões {level_name} para avaliar se você já pode ir "
            "para as {next_name}."
        ),
        "keep_practicing_accuracy": (
            "Nas últimas {attempts} questões {level_name}, o acerto foi {percent}%. "
            "Para avançar, precisa de {needed_percent}%."
        ),
        "reinforce": (
            "Seu acerto recente em questões {level_name} ficou abaixo de {reinforce_percent}%. "
            "Vale reforçar as questões {previous_name}."
        ),
        "not_enough_questions": (
            "Este tópico só tem {available} questões {level_name}. Acerte pelo menos "
            "{needed_percent}% de todas para liberar as {next_name}."
        ),
        "max_level": "Você já liberou as questões {level_name} de {topic_name}. Continue praticando.",
    }
    WEEKLY_MIN_ANSWERS_PER_TOPIC = int(os.getenv("WEEKLY_MIN_ANSWERS_PER_TOPIC", "5"))
    WEEKLY_DELTA_PP = int(os.getenv("WEEKLY_DELTA_PP", "10"))
    REVIEW_INTERVALS_DAYS = tuple(
        int(part.strip())
        for part in os.getenv("REVIEW_INTERVALS_DAYS", "1,3,7").split(",")
        if part.strip()
    )
    MAIL_BACKEND = os.getenv("MAIL_BACKEND", "console")
    MAIL_SERVER = os.getenv("MAIL_SERVER") or os.getenv("SMTP_HOST", "")
    MAIL_PORT = int(os.getenv("MAIL_PORT") or os.getenv("SMTP_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}
    MAIL_USERNAME = os.getenv("MAIL_USERNAME") or os.getenv("SMTP_USER", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD") or os.getenv("SMTP_PASSWORD") or _secret(
        "MAIL_PASSWORD", ""
    )
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv(
        "SMTP_FROM", "nao-responda@proenem.lab"
    )
    NOTIFY_MAX_PER_DAY = int(os.getenv("NOTIFY_MAX_PER_DAY", "4"))
    NOTIFY_MAX_DELAY_MINUTES = int(os.getenv("NOTIFY_MAX_DELAY_MINUTES", "90"))
    NOTIFY_DISPATCH_EVERY_MINUTES = int(os.getenv("NOTIFY_DISPATCH_EVERY_MINUTES", "15"))
    NOTIFY_TEST_MAX_PER_HOUR = int(os.getenv("NOTIFY_TEST_MAX_PER_HOUR", "3"))
    STUDY_BLOCK_REMINDER_MINUTES = int(os.getenv("STUDY_BLOCK_REMINDER_MINUTES", "10"))
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "false").lower() in {"1", "true", "yes"}
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY") or _secret("VAPID_PRIVATE_KEY", "")
    VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:nao-responda@proenem.lab")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:5000")
    INEP_EXAM_WINDOW = int(os.getenv("INEP_EXAM_WINDOW", "5"))
    ENEM_OBJECTIVE_QUESTIONS_PER_EDITION = int(
        os.getenv("ENEM_OBJECTIVE_QUESTIONS_PER_EDITION", "180")
    )
    ROADMAP_MIN_COVERAGE = float(os.getenv("ROADMAP_MIN_COVERAGE", "0.90"))
    ROADMAP_DATA_DIR = os.getenv(
        "ROADMAP_DATA_DIR", os.path.join(_BACKEND_ROOT, "repositories", "data", "roadmap")
    )
    EXPORT_PDF_MAX_PER_HOUR = int(os.getenv("EXPORT_PDF_MAX_PER_HOUR", "10"))
    EXPORT_PDF_MAX_QUESTIONS = int(os.getenv("EXPORT_PDF_MAX_QUESTIONS", "1000"))
    EXPORT_PDF_MAX_NOTES = int(os.getenv("EXPORT_PDF_MAX_NOTES", "2000"))

class DevelopmentConfig(Config):
    DEBUG = True
    MAIL_BACKEND = os.getenv("MAIL_BACKEND", "console")

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "testing-secret-key-proenem-lab-fase1"
    JWT_SECRET_KEY = "testing-jwt-secret-proenem-lab-fase1"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    ENEM_AUTO_SYNC = False
    MAIL_BACKEND = "console"
    SCHEDULER_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
