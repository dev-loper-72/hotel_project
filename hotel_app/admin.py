from django.contrib import admin
from .models import Guest, Room, RoomType, Reservation
# Register the models for the admin page
admin.site.register(Guest)
admin.site.register(Room)
admin.site.register(RoomType)
admin.site.register(Reservation)