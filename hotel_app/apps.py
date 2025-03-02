from django.apps import AppConfig
import logging

# Configure logging
logger = logging.getLogger(__name__)


class HotelAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hotel_app'

    def ready(self):
        """
        Override the ready method to add initialization logging.
        """
        super().ready()
        logger.info(f"{self.name} app is ready with default auto field {self.default_auto_field}")
