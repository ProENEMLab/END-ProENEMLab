import logging
import os

from flask import Flask

logger = logging.getLogger(__name__)

def register_scheduler(app: Flask) -> None:
    if not app.config.get("SCHEDULER_ENABLED"):
        return
    if app.config.get("TESTING"):
        return
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = BackgroundScheduler(timezone=app.config.get("APP_TIMEZONE") or "America/Sao_Paulo")
    minutes = int(app.config.get("NOTIFY_DISPATCH_EVERY_MINUTES") or 15)
    scheduler.add_job(
        lambda: _run_dispatch(app),
        IntervalTrigger(minutes=minutes),
        id="notifications-dispatch",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        lambda: _run_roadmap_draft(app),
        CronTrigger(month=1, day=15, hour=8, minute=0),
        id="roadmap-annual-draft",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    app.extensions["scheduler"] = scheduler
    logger.info(
        "Agendador ligado: lembretes a cada %s min e rascunho do roadmap em 15/01 08:00", minutes
    )

def _run_dispatch(app: Flask) -> None:
    with app.app_context():
        from container import dispatcher_service

        try:
            dispatcher_service.dispatch()
        except Exception:
            logger.exception("Disparo de lembretes falhou")

def _run_roadmap_draft(app: Flask) -> None:
    with app.app_context():
        from container import roadmap_version_service
        from services.roadmap_catalog import RoadmapDataError

        try:
            roadmap_version_service.scheduled_build()
        except RoadmapDataError:
            logger.exception("Rascunho anual do roadmap não foi gerado")
        except Exception:
            logger.exception("Rascunho anual do roadmap não foi gerado")
