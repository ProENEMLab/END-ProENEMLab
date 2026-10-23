from config import Config
from controllers.auth_controller import AuthController
from controllers.calendar_controller import CalendarController
from controllers.dashboard_controller import DashboardController
from controllers.enem_controller import EnemController
from controllers.export_controller import StudyReportController
from controllers.filter_set_controller import FilterSetController
from controllers.goal_controller import GoalController
from controllers.health_controller import HealthController
from controllers.note_controller import NoteController
from controllers.notification_controller import NotificationController
from controllers.plans_controller import PlansController
from controllers.points_controller import PointsController
from controllers.question_controller import QuestionController
from controllers.roadmap_controller import RoadmapController
from controllers.stats_controller import StatsController
from controllers.streak_controller import StreakController
from controllers.study_controller import (
    ExportController,
    IncidenceController,
    ProgressionController,
    ReportController,
    ReviewController,
)
from controllers.testimonial_controller import TestimonialController
from services.clock import Clock
from repositories.attempt_repository import AttemptRepository
from repositories.calendar_repository import CalendarRepository
from repositories.filter_repository import FilterRepository
from repositories.goal_repository import GoalRepository
from repositories.inep_item_repository import InepItemRepository
from repositories.insight_repository import IncidenceRepository, ReportRepository
from repositories.learning_repository import ProgressionRepository, ReviewRepository
from repositories.note_repository import NoteRepository
from repositories.notification_repository import ExportRepository, NotificationRepository
from repositories.option_repository import OptionRepository
from repositories.points_repository import PointsRepository
from repositories.progress_repository import ProgressRepository
from repositories.question_repository import QuestionRepository
from repositories.roadmap_version_repository import RoadmapVersionRepository
from repositories.streak_repository import StreakRepository
from repositories.study_report_repository import StudyReportRepository
from repositories.testimonial_repository import TestimonialRepository
from repositories.topic_repository import TopicRepository
from repositories.user_repository import UserRepository
from services.auth_service import AuthService
from services.dashboard_service import DashboardService
from services.difficulty_service import DifficultyService
from services.enem_service import EnemService
from services.export_rate_limiter import ExportRateLimiter
from services.export_service import ExportService
from services.filter_sets_service import FilterSetsService
from services.focus_service import FocusService
from services.goals_service import GoalsService
from services.incidence_service import IncidenceService
from services.inep_import_service import InepImportService
from services.notes_service import NotesService
from services.notifications.channels.email_sender import RoutingEmailSender
from services.notifications.channels.push_sender import WebPushSender
from services.notifications.dispatcher_service import DispatcherService
from services.notifications.notification_service import NotificationService
from services.plans_service import PlansService
from services.points_service import PointsService
from services.progression_service import ProgressionService
from services.questions_service import QuestionsService
from services.report_service import WeeklyReportService
from services.review_service import ReviewService
from services.roadmap_service import RoadmapService
from services.roadmap_version_service import RoadmapVersionService
from services.stats_service import StatsService
from services.streak_service import StreakService
from services.study_block_service import StudyBlockService
from services.study_report_service import StudyReportService
from services.study_rules import CalendarLimits
from services.study_session_service import StudySessionService
from services.testimonials_service import TestimonialsService

clock = Clock()

user_repository = UserRepository()
calendar_repository = CalendarRepository()
progression_repository = ProgressionRepository()
review_repository = ReviewRepository()
report_repository = ReportRepository()
incidence_repository = IncidenceRepository()
notification_repository = NotificationRepository()
export_repository = ExportRepository()
topic_repository = TopicRepository()
progress_repository = ProgressRepository()
note_repository = NoteRepository()
question_repository = QuestionRepository()
inep_item_repository = InepItemRepository()
option_repository = OptionRepository()
attempt_repository = AttemptRepository()
goal_repository = GoalRepository()
points_repository = PointsRepository()
streak_repository = StreakRepository()
filter_repository = FilterRepository()
testimonial_repository = TestimonialRepository()
roadmap_version_repository = RoadmapVersionRepository()

points_service = PointsService(points_repository, user_repository)
streak_service = StreakService(streak_repository, points_service)
auth_service = AuthService(user_repository)
roadmap_version_service = RoadmapVersionService(
    roadmap_version_repository,
    topic_repository,
    question_repository,
    inep_item_repository,
    clock,
)
roadmap_service = RoadmapService(topic_repository, progress_repository, roadmap_version_service)
notes_service = NotesService(note_repository, topic_repository)
calendar_limits = CalendarLimits.from_config(Config)
study_block_service = StudyBlockService(calendar_repository, clock, calendar_limits)
study_session_service = StudySessionService(calendar_repository, clock, calendar_limits)
focus_service = FocusService(calendar_repository, clock)
difficulty_service = DifficultyService(
    question_repository, inep_item_repository, attempt_repository
)
inep_import_service = InepImportService(
    inep_item_repository, question_repository, difficulty_service
)
review_service = ReviewService(review_repository, clock)
progression_service = ProgressionService(
    progression_repository, question_repository, topic_repository
)
report_service = WeeklyReportService(
    report_repository,
    calendar_repository,
    review_repository,
    clock,
    min_answers=Config.WEEKLY_MIN_ANSWERS_PER_TOPIC,
    delta_pp=Config.WEEKLY_DELTA_PP,
)
incidence_service = IncidenceService(incidence_repository, topic_repository, clock)
export_service = ExportService(export_repository, topic_repository)
study_report_repository = StudyReportRepository()
study_report_service = StudyReportService(
    study_report_repository,
    user_repository,
    clock,
    ExportRateLimiter(Config.EXPORT_PDF_MAX_PER_HOUR),
)
questions_service = QuestionsService(
    question_repository,
    attempt_repository,
    points_service,
    streak_service,
    review_service,
)
goals_service = GoalsService(goal_repository, points_service, streak_service)
notification_service = NotificationService(
    notification_repository,
    user_repository,
    goals_service,
    review_service,
    streak_service,
    focus_service,
    calendar_repository,
    clock,
    RoutingEmailSender(),
    WebPushSender(),
)
dispatcher_service = DispatcherService(notification_repository, notification_service, clock)
stats_service = StatsService(attempt_repository)
filter_sets_service = FilterSetsService(filter_repository)
testimonials_service = TestimonialsService(testimonial_repository)
enem_service = EnemService(question_repository, option_repository)
plans_service = PlansService()
dashboard_service = DashboardService(roadmap_service, goals_service, streak_service)

auth_controller = AuthController(auth_service)
roadmap_controller = RoadmapController(roadmap_service)
note_controller = NoteController(notes_service)
question_controller = QuestionController(questions_service, progression_service)
calendar_controller = CalendarController(study_block_service, study_session_service, focus_service)
review_controller = ReviewController(review_service, questions_service)
progression_controller = ProgressionController(progression_service)
report_controller = ReportController(report_service)
incidence_controller = IncidenceController(incidence_service)
export_controller = ExportController(export_service)
study_report_controller = StudyReportController(study_report_service)
notification_controller = NotificationController(notification_service)
enem_controller = EnemController(enem_service)
goal_controller = GoalController(goals_service)
points_controller = PointsController(points_service)
streak_controller = StreakController(streak_service)
stats_controller = StatsController(stats_service)
dashboard_controller = DashboardController(dashboard_service)
filter_set_controller = FilterSetController(filter_sets_service)
plans_controller = PlansController(plans_service)
testimonial_controller = TestimonialController(testimonials_service)
health_controller = HealthController()
