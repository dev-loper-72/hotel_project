from django.urls import path, include
from . import views

# Define list of url patterns
urlpatterns = [
    path('', views.home_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    # Guest URLs
    path('guest/', views.guest_list_view, name="guest_list"),
    path('guest/create/', views.guest_create_view, name="guest_create"),
    path('guest/<int:guest_id>/update/', views.guest_update_view, name="guest_update"),
    path('guest/<int:guest_id>/delete/', views.guest_delete_view, name="guest_delete"),  
    # URLs to support room reservation process, from finding Available Rooms, to Reserving the room, to Selecting a guest 
    path("available-rooms/", views.available_rooms_list_view, name="available_rooms_list"),
    path("available-rooms/<int:room_number>/reserve", views.available_rooms_reserve_view, name="available_rooms_reserve"),  # redirect to Create a new Reservation
    path('available-rooms/guest-selection/', views.available_rooms_guest_selection_view, name="available_rooms_guest_selection"),
    # Reservation URLs
    path("reservation/", views.reservation_list_view, name="reservation_list"),  # List all Reservation
    path("reservation/create/<int:guest_id>", views.reservation_create_view, name="reservation_create"),  # Create a new Reservation for a guest
    path("reservation/<int:reservation_id>/update/", views.reservation_update_view, name="reservation_update"),  # Edit a Reservation
    path("reservation/<int:reservation_id>/delete/", views.reservation_delete_view, name="reservation_delete"),  # Delete a Reservation
    path('reservation/<int:reservation_id>/confirmed', views.reservation_confirmed_view, name="reservation_confirmed"), # Show Reservation Confirmation
    # Room URLs
    path("room/", views.room_list_view, name="room_list"),  # List all Rooms
    path("room/create/", views.room_create_view, name="room_create"),  # Create a new Room
    path("room/<int:room_number>/update/", views.room_update_view, name="room_update"),  # Edit a Room
    path("room/<int:room_number>/delete/", views.room_delete_view, name="room_delete"),  # Delete a Room
    # RoomType URLs
    path("room-types/", views.room_type_list_view, name="room_type_list"),  # List all RoomTypes
    path("room-types/create/", views.room_type_create_view, name="room_type_create"),  # Create a new RoomType
    path("room-types/<str:room_type_code>/update/", views.room_type_update_view, name="room_type_update"),  # Edit a RoomType
    path("room-types/<str:room_type_code>/delete/", views.room_type_delete_view, name="room_type_delete"),  # Delete a RoomType
    # API URLs
    path('api/', views.api_root, name='api-root'),
    path('api/guest/', views.APIGuestListCreate.as_view(), name="api_guest_list_create"),
    path('api/guest/<int:pk>/', views.APIGuestRetrieveUpdateDestroy.as_view(), name="api_guest_update_destroy"),
    path('api/reservation/', views.APIReservationListCreate.as_view(), name="api_reservation_list_create"),
    path('api/reservation/<int:pk>/', views.APIReservationRetrieveUpdateDestroy.as_view(), name="api_reservation_update_destroy"),
    path('api/room/', views.APIRoomListCreate.as_view(), name="api_room_list_create"),
    path('api/room/<int:pk>/', views.APIRoomRetrieveUpdateDestroy.as_view(), name="api_room_update_destroy"),
    path('api/room-type/', views.APIRoomTypeListCreate.as_view(), name="api_room_type_list_create"),
    path('api/room-type/<str:pk>/', views.APIRoomTypeRetrieveUpdateDestroy.as_view(), name="api_room_type_update_destroy"),  
]