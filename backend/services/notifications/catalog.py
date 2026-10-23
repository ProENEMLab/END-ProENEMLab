REMINDER_TYPES = ("daily_goal", "reviews_due", "streak_at_risk", "study_block")
TIMED_TYPES = ("daily_goal", "reviews_due", "streak_at_risk")
CHANNELS = ("email", "push")

LINKS = {
    "daily_goal": "/pages/dashboard/index.html",
    "reviews_due": "/pages/reviews/index.html",
    "streak_at_risk": "/pages/dashboard/index.html",
    "study_block": "/pages/calendar/index.html",
}

LABELS = {
    "daily_goal": "meta diária",
    "reviews_due": "revisões",
    "streak_at_risk": "sequência",
    "study_block": "bloco de estudo",
    "email": "e-mail",
    "push": "navegador",
}

def default_types() -> dict:
    return {
        "daily_goal": {"email": False, "push": False, "time": "20:00"},
        "reviews_due": {"email": False, "push": False, "time": "08:00"},
        "streak_at_risk": {"email": False, "push": False, "time": "21:00"},
        "study_block": {"email": False, "push": False},
    }

def default_preferences() -> dict:
    return {
        "email_enabled": False,
        "push_enabled": False,
        "quiet_start": "22:00",
        "quiet_end": "07:00",
        "types": default_types(),
    }
