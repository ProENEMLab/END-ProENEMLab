import os

from flask import Flask

from controllers.cli_controller import (
    add_testimonial_command,
    difficulty_group,
    inep_group,
    notifications_group,
    refresh_incidence_command,
    reports_group,
    roadmap_group,
    seed_command,
    sync_enem_command,
)
from config import config_by_name
from extensions import cors, db, jwt

def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(_select_config(config_name))
    _init_extensions(app)
    _register_api(app)
    _register_commands(app)
    with app.app_context():
        db.create_all()
    return app

def _select_config(config_name: str | None):
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(config_name, config_by_name["development"])

def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(
        app,
        resources={
            r"/api/*": {"origins": app.config.get("CORS_ORIGINS", ["http://localhost:5173"])}
        },
        expose_headers=["Content-Disposition"],
    )

def _register_api(app: Flask) -> None:
    import models
    from controllers import register_blueprints
    from controllers.error_handlers import register_error_handlers

    register_error_handlers(app)
    register_blueprints(app)
    from controllers.notification_jobs import register_scheduler

    register_scheduler(app)

def _register_commands(app: Flask) -> None:
    app.cli.add_command(seed_command)
    app.cli.add_command(sync_enem_command)
    app.cli.add_command(add_testimonial_command)
    app.cli.add_command(refresh_incidence_command)
    app.cli.add_command(reports_group)
    app.cli.add_command(notifications_group)
    app.cli.add_command(inep_group)
    app.cli.add_command(difficulty_group)
    app.cli.add_command(roadmap_group)
