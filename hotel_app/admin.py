from django.contrib import admin
import logging
from .models import Guest, Room, RoomType, Reservation

# Configure logging
logger = logging.getLogger(__name__)

# Register the models for the admin page
admin.site.register(Guest)
logger.info("Registered Guest model with admin site")

admin.site.register(Room)
logger.info("Registered Room model with admin site")

admin.site.register(RoomType)
logger.info("Registered RoomType model with admin site")

admin.site.register(Reservation)
logger.info("Registered Reservation model with admin site")