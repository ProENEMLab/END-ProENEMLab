class ApiError(Exception):

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str | None = None,
        extra: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.extra = extra or {}

class AuthError(ApiError):
    pass

class QuestionsError(ApiError):
    pass

class RoadmapError(ApiError):
    pass

class NotesError(ApiError):
    pass

class GoalsError(ApiError):
    pass

class PointsError(ApiError):
    pass

class StreakError(ApiError):
    pass

class StatsError(ApiError):
    pass

class FilterSetError(ApiError):
    pass

class TestimonialError(ApiError):
    pass

class CalendarError(ApiError):
    pass

class ReviewError(ApiError):
    pass

class ProgressionError(ApiError):
    pass

class ExportError(ApiError):
    pass

class NotificationError(ApiError):
    pass

class EnemApiError(ApiError):

    def __init__(
        self,
        message: str,
        status_code: int = 502,
        code: str = "ENEM_API_ERROR",
    ) -> None:
        super().__init__(message, status_code, code)
