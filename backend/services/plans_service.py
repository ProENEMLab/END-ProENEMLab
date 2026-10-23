from services.plans_catalog import get_catalog

class PlansService:

    def get_catalog(self) -> dict:
        return get_catalog()
