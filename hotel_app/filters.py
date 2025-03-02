"""
This module defines filters for the hotel management application using the Django filters framework.
It includes filters for Guests, Reservations, and Available Rooms.
"""

import logging
from datetime import timedelta, datetime
import django_filters
from django import forms
from django.db.models import F, ExpressionWrapper, IntegerField
from django.utils import timezone
from .models import Guest, Reservation, Room, RoomType

# Configure logging
logger = logging.getLogger(__name__)

# Filter for use by the Guest list
class GuestFilter(django_filters.FilterSet):
    """
    Filter for the Guest list with validation.

    This filter allows searching guests by last name and postcode with format validation.
    """
    last_name = django_filters.CharFilter(
        label="Last name",
        field_name='last_name',
        lookup_expr='iexact',
        widget=forms.TextInput(attrs={
            'pattern': r'^[A-Za-z\-\' ]+$',
            'title': 'Last name can only contain letters, hyphens, apostrophes and spaces'
        })
    )

    postcode = django_filters.CharFilter(
        label="Postcode",
        method='filter_postcode',
        widget=forms.TextInput(attrs={
            'pattern': r'^[A-Za-z][A-Ha-hJ-Yj-y]?\d[A-Za-z\d]? ?\d[A-Za-z]{2}$',
            'title': 'Please enter a valid UK postcode'
        })
    )

    def validate_postcode(self, value):
        """Validate postcode format before filtering."""
        if value:
            # Basic UK postcode validation
            import re
            pattern = r'^[A-Za-z][A-Ha-hJ-Yj-y]?\d[A-Za-z\d]? ?\d[A-Za-z]{2}$'
            if not re.match(pattern, value.upper().strip()):
                return False, "Please enter a valid UK postcode"
        return True, None

    def validate_last_name(self, value):
        """Validate last name format before filtering."""
        if value and not value.replace("'", "").replace("-", "").replace(" ", "").isalpha():
            return False, "Last name can only contain letters, hyphens, apostrophes and spaces"
        return True, None

    def filter_postcode(self, queryset, _, value):
        """
        Custom filter method for postcode that handles validation and matching.
        """
        logger.info(f"Filtering guests by postcode: {value}")

        # Validate postcode format
        is_valid, error = self.validate_postcode(value)
        if not is_valid:
            logger.warning(f"Invalid postcode format: {value}")
            return queryset.none()  # Return empty queryset for invalid input

        if value:
            if self.data.get('last_name'):
                # If last_name is also provided, do exact match
                logger.info(f"Exact match for postcode as last_name is also provided: {value}")
                return queryset.filter(postcode__iexact=value.upper().strip())
            else:
                # If only postcode filter is applied, do partial match on outward code
                postcode = value.upper().strip()
                outward_code = postcode.split()[0]  # Get the outward code (e.g., 'SW1A')
                logger.info(f"Partial match for postcode outward code: {outward_code}")
                return queryset.filter(postcode__istartswith=outward_code)

    @property
    def qs(self):
        """Override queryset to add validation."""
        qs = super().qs
        if self.data.get('last_name'):
            is_valid, error = self.validate_last_name(self.data['last_name'])
            if not is_valid:
                logger.warning(f"Invalid last name format: {self.data['last_name']}")
                return self.queryset.none()  # Return empty queryset for invalid input
        return qs

    class Meta:
        model = Guest
        fields = ['last_name', 'postcode']

# Filter for use by the Reservations list
class ReservationFilter(django_filters.FilterSet):
    """
    Filter for the Reservations list.

    This filter allows searching reservations by guest name, room number, start date, and end date.
    """
    last_name = django_filters.CharFilter(
        label="Guest name",
        field_name='guest__last_name',
        lookup_expr='icontains',
        method='validate_last_name'
    )
    room_number = django_filters.NumberFilter(
        label="Room",
        field_name='room_number',
        lookup_expr='exact',
        min_value=1,
        max_value=9999  # Adjust based on your hotel's maximum room number
    )
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

    def validate_last_name(self, queryset, name, value):
        """
        Validate and filter by last name.

        Args:
            queryset: The initial queryset
            name: Field name being filtered
            value: The value to filter by

        Returns:
            Filtered queryset or empty queryset if validation fails
        """
        if not value:
            return queryset

        # Remove any leading/trailing whitespace
        value = value.strip()

        # Check if value contains only letters, spaces, hyphens and apostrophes
        if not all(c.isalpha() or c in [' ', '-', "'"] for c in value):
            logger.warning(f"Invalid last name format: {value}")
            # Store validation error message
            if not hasattr(self, 'validation_messages'):
                self.validation_messages = []
            self.validation_messages.append(f"Invalid guest name format: '{value}'. Only letters, spaces, hyphens and apostrophes are allowed.")
            return queryset.none()

        return queryset.filter(guest__last_name__icontains=value)

    class Meta:
        model = Reservation
        fields = ['start_date', 'end_date', 'last_name', 'room_number']


# Filter for use by the Available Rooms list when searching for availability
# for a specific booking request (start date and number of nights)
# Also supports filtering by room type
class RoomFilter(django_filters.FilterSet):
    """
    Filter for the Room list.

    This filter allows searching rooms by room number and room type.
    """
    room_number = django_filters.NumberFilter(
        label="Room Number",
        field_name='room_number',
        lookup_expr='exact',
        min_value=1,
        max_value=9999
    )
    room_type = django_filters.ModelChoiceFilter(
        queryset=RoomType.objects.all(),
        field_name="room_type",
        empty_label="All Room Types"
    )

    class Meta:
        model = Room
        fields = ['room_number', 'room_type']


class AvailableRoomFilter(django_filters.FilterSet):
    """
    Filter for the Available Rooms list.

    This filter allows searching for available rooms based on start date, length of stay, and room type.
    """
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


    def filter_queryset(self, queryset):
        """
        Custom version of filter_queryset to exclude any rooms that will be occupied
        on the night of the start date or any of the following 'length of stay' nights.
        Also excludes rooms that don't match the requested room type.

        Args:
            queryset: The initial queryset of rooms.

        Returns:
            QuerySet: The filtered queryset.
        """
        logger.info("Filtering available rooms based on search criteria.")
        data = self.data
        start_date = data.get("start_date")
        length_of_stay = data.get("length_of_stay")
        room_type = data.get("room_type")

        # filter by date range
        if start_date and length_of_stay:
            logger.info(f"Filtering rooms for start date: {start_date} and length of stay: {length_of_stay}")
            # Convert `start_date` from string to timezone-aware datetime
            start_date_for_filter = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
            length_of_stay = int(length_of_stay)
            end_date_for_filter = start_date_for_filter + timedelta(days=length_of_stay)

            # find any rooms that are reserved at any point between the start_date and the end_date of the filter
            reserved_rooms = Reservation.objects.filter(
                start_of_stay__lt=end_date_for_filter,
                end_date__gt=start_date_for_filter
            ).values_list("room_number", flat=True)

            # exclude those rooms
            logger.info(f"Excluding reserved rooms: {list(reserved_rooms)}")
            queryset = queryset.exclude(room_number__in=reserved_rooms)

        # filter by room type (if specified)
        if room_type:
            logger.info(f"Filtering rooms by room type: {room_type}")
            queryset = queryset.filter(room_type__room_type_code=room_type)

        return queryset
    
  

