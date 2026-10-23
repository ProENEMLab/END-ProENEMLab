from flask import Flask

def register_blueprints(app: Flask) -> None:
    from controllers.auth_controller import auth_bp, bind_auth_routes
    from controllers.calendar_controller import bind_calendar_routes, calendar_bp
    from controllers.dashboard_controller import bind_dashboard_routes, dashboard_bp
    from controllers.export_controller import bind_export_routes, study_report_bp
    from controllers.filter_set_controller import bind_filter_set_routes, filter_sets_bp
    from controllers.goal_controller import bind_goal_routes, goals_bp
    from controllers.health_controller import bind_health_routes, health_bp
    from controllers.note_controller import bind_note_routes, notes_bp
    from controllers.notification_controller import bind_notification_routes, notification_bp
    from controllers.plans_controller import bind_plans_routes, plans_bp
    from controllers.points_controller import bind_points_routes, points_bp
    from controllers.question_controller import bind_question_routes, questions_bp
    from controllers.roadmap_controller import bind_roadmap_routes, roadmap_bp
    from controllers.stats_controller import bind_stats_routes, stats_bp
    from controllers.streak_controller import bind_streak_routes, streak_bp
    from controllers.study_controller import (
        bind_study_routes,
        export_bp,
        incidence_bp,
        progression_bp,
        report_bp,
        review_bp,
    )
    from controllers.testimonial_controller import bind_testimonial_routes, testimonials_bp

    bind_health_routes()
    bind_auth_routes()
    bind_roadmap_routes()
    bind_note_routes()
    bind_question_routes()
    bind_filter_set_routes()
    bind_plans_routes()
    bind_testimonial_routes()
    bind_goal_routes()
    bind_points_routes()
    bind_streak_routes()
    bind_stats_routes()
    bind_dashboard_routes()
    bind_calendar_routes()
    bind_study_routes()
    bind_export_routes()
    bind_notification_routes()

    for blueprint in (
        health_bp,
        auth_bp,
        roadmap_bp,
        notes_bp,
        questions_bp,
        filter_sets_bp,
        plans_bp,
        testimonials_bp,
        goals_bp,
        points_bp,
        streak_bp,
        stats_bp,
        dashboard_bp,
        calendar_bp,
        review_bp,
        progression_bp,
        report_bp,
        incidence_bp,
        export_bp,
        study_report_bp,
        notification_bp,
    ):
        app.register_blueprint(blueprint)
