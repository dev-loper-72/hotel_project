# Using the django filters framework, this file defines 
# filters to be used by the app

import django_filters
from django import forms
from django.db.models import Func,F, ExpressionWrapper, IntegerField, DateField, DurationField
from django.utils import timezone
from . models import Guest, Reservation, Room, RoomType
from datetime import timedelta, datetime

# Filter for use by the Guest list
class GuestFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(label="Last name", field_name='last_name', lookup_expr='icontains')
    postcode = django_filters.CharFilter(label="Postcode", field_name='postcode', lookup_expr='icontains')

    class Meta:
        model = Guest
        fields = ['last_name', 'postcode']

# Filter for use by the Reservations list, need to show any reservation that falls inside the search criteria
# Note: needs to consider the end_date of the reservation when deciding if any of the reservation falls inside the search window
class ReservationFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(label="Guest name", field_name='guest__last_name', lookup_expr='icontains')
    room_number = django_filters.CharFilter(label="Room", field_name='room_number', lookup_expr='exact')
    start_date = django_filters.DateFilter(
        field_name="end_date",
        lookup_expr="gte",
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="start_of_stay",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),  
        label="End Date"
    )
        
    class Meta:
        model = Reservation
        fields = ['start_date', 'end_date', 'last_name', 'room_number']   


# Filter for use by the Available Rooms list when searching for availablility 
# for a specific booking request (start date and number of nights)
# Also supports filtering by room type
class AvailableRoomFilter(django_filters.FilterSet):
    start_date = django_filters.DateFilter(
        field_name="reservations__start_of_stay",
        lookup_expr="gte",
        widget=forms.DateInput(attrs={"type": "date"}), 
        label="Date of Stay"
    )
    length_of_stay = django_filters.NumberFilter(
        widget=forms.NumberInput(attrs={"min": 1}), 
        label="Number of nights"
    )
    room_type = django_filters.ModelChoiceFilter(
        queryset=RoomType.objects.all(),
        field_name="room_type",
        empty_label="All Room Types"
    )

    class Meta:
        model = Room
        fields = ["start_date", "length_of_stay", "room_type"]


    # Custom version of filter_queryset to exclude any rooms that will be occupied 
    # on the night of the start date or any of the following 'length of stay' nights
    # Also excludes rooms that don't match the requested room type
    def filter_queryset(self, queryset):
        data = self.data
        start_date = data.get("start_date")
        length_of_stay = data.get("length_of_stay")
        room_type = data.get("room_type")

        # filter by date range
        if start_date and length_of_stay:
            # Convert `start_date` from string to timezone-aware datetime
            start_date_for_filter = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
            #start_date = datetime.strptime(start_date, '%Y-%m-%d')
            length_of_stay = int(length_of_stay)
            end_date_for_filter = start_date_for_filter + timedelta(days=length_of_stay)

            # find any rooms that are reserved at any point between the start_date and the end_date of the filter
            reserved_rooms = Reservation.objects.filter(
                start_of_stay__lt=end_date_for_filter,
                end_date__gt=start_date_for_filter
            ).values_list("room_number", flat=True)

            # exclude those rooms
            queryset = queryset.exclude(room_number__in=reserved_rooms)

        # filter by room type (if specified)
        if room_type:
            queryset = queryset.filter(room_type__room_type_code=room_type)

        return queryset  
