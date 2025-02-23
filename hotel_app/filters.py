# Using the django filters framework, this file defines 
# filters to be used by the app

import django_filters
from django import forms
from django.db.models import F, ExpressionWrapper, IntegerField
from . models import Guest, Reservation, Room, RoomType
from datetime import timedelta, datetime

# Filter for use by the Guest list
class GuestFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(label="Last name", field_name='last_name', lookup_expr='icontains')
    postcode = django_filters.CharFilter(label="Postcode", field_name='postcode', lookup_expr='icontains')

    class Meta:
        model = Guest
        fields = ['last_name', 'postcode']

# Filter for use by the Reservations list
class ReservationFilter(django_filters.FilterSet):
    last_name = django_filters.CharFilter(label="Guest name", field_name='guest__last_name', lookup_expr='icontains')
    room_number = django_filters.CharFilter(label="Room", field_name='room_number', lookup_expr='exact')
    start_date = django_filters.DateFilter(
        field_name="start_of_stay",
        label="Start Date",
        method="filter_start_including_stay_length",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = django_filters.DateFilter(
        field_name="start_of_stay",
        lookup_expr="lte",
        widget=forms.DateInput(attrs={"type": "date"}),  
        label="End Date"
    )
    
    # When filtering by an entered start date, the list needs to include reservations that start before the entered
    # date, but due to their length_of_stay, are still occupying a room on between start & end date
    def filter_start_including_stay_length(self, queryset, name, value):
        
        #Filters reservations where the number of days between start_of_stay and start_date
        #is greater than length_of_stay.

        # calculate days_between in the database
        # - it calculates the difference between the start of the stay and the entered filter start date
        # - divides by 86400000000 to convert that value into days 
        #       (Note: other day extraction options didn't seem to work with sqlite3 database)
        # - adds the length_of_stay to base the filter on the end of the stay rather than the start        
        queryset = queryset.annotate(
            days_between=ExpressionWrapper(
                ((F('start_of_stay') -value)/86400000000)+ F('length_of_stay'), output_field=IntegerField() # convert to whole days
            )
        )
       
        # Debug code to discover if days_between is being calculated correctly   
        #for reservation in queryset.values('reservation_id', 'start_of_stay', 'length_of_stay', 'days_between'):
        #    print(f"Reservation ID: {reservation['reservation_id']}, "
        #                 f"Start of Stay: {reservation['start_of_stay']}, "
        #                 f"Length of Stay: {reservation['length_of_stay']}, "
        #                 f"Days Between: {reservation['days_between']}")
            
        # if days_between >= 0 then the reservation will have ended before the filter start date and so the reservation can be excluded
        return queryset.filter(days_between__gte=0)


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
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            length_of_stay = int(length_of_stay)
            end_date = start_date + timedelta(days=length_of_stay)

            reserved_rooms = Reservation.objects.filter(
                start_of_stay__lt=end_date,
                start_of_stay__gte=start_date
            ).values_list("room_number", flat=True)

            queryset = queryset.exclude(room_number__in=reserved_rooms)

        # filter by room type (if specified)
        if room_type:
            queryset = queryset.filter(room_type__room_type_code=room_type)

        return queryset  
    
  
