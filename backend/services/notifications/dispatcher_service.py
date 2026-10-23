from services.clock import Clock
from repositories.notification_repository import NotificationRepository
from services.notifications.notification_service import NotificationService

class DispatcherService:

    def __init__(
        self,
        notification_repository: NotificationRepository,
        notification_service: NotificationService,
        clock: Clock,
    ) -> None:
        self.notifications = notification_repository
        self.service = notification_service
        self.clock = clock

    def dispatch(self) -> dict:
        now = self.clock.now_local()
        sent = 0
        considered = 0
        for pref in self.notifications.list_with_channel_enabled():
            if not self.service.is_in_window(pref, now):
                continue
            considered += 1
            sent += self.service.dispatch_user(pref, now)
        return {"sent": sent, "considered": considered}
