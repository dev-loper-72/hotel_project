# django data models that will be used to create & maintain the database tables
# to store data entered by the user
from datetime import timedelta
import logging
from django.db.models import F, ExpressionWrapper, IntegerField
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.db import models

def validate_title(value):
    valid_titles = ['Mr', 'Miss', 'Mrs', 'Ms', 'Dr', 'Prof', 'Sir', 'Dame']
    if value not in valid_titles:
        raise ValidationError(
            f'{value} is not a valid title. Please use one of: {", ".join(valid_titles)}'
        )

def validate_guest_count(reservation, room):    
    """Validate that the number of guests doesn't exceed room capacity."""
    if reservation.number_of_guests > room.room_type.maximum_guests:
        raise ValidationError(
            f'Number of guests ({reservation.number_of_guests}) exceeds room capacity ({room.room_type.maximum_guests})'
        )
    if reservation.number_of_guests < 1:
        raise ValidationError('Number of guests must be at least 1')

def validate_payment(amount_paid, total_price):
    """Validate that the payment amount is valid."""
    if amount_paid is None:
        raise ValidationError('Payment amount is required')
    if amount_paid < 0:
        raise ValidationError('Please enter a valid payment amount (must be 0 or greater)')
    if total_price is not None and amount_paid > total_price:
        raise ValidationError('Payment amount cannot exceed the total price')

# Configure logging
logger = logging.getLogger(__name__)

class Guest(models.Model):
    """
    Model representing a hotel guest with their personal and contact information.

    This model stores comprehensive guest details including name, contact information,
    and full address for booking and communication purposes.
    """
    guest_id = models.AutoField(primary_key=True)  # Unique identifier for each guest
    title = models.CharField(
        max_length=10,
        validators=[validate_title]
    )  # Guest's title (Mr., Mrs., Ms., etc.)
    first_name = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                r'^[A-Za-z\-\' ]+$',
                message="First name can only contain letters, hyphens, apostrophes and spaces"
            )
        ]
    )  # Guest's first name
    last_name = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                r'^[A-Za-z\-\' ]+$',
                message="Last name can only contain letters, hyphens, apostrophes and spaces"
            )
        ]
    )  # Guest's last name
    phone_number = models.CharField(
        max_length=11,
        validators=[
            RegexValidator(
                r'^(07\d{9}|0\d{10})$',
                message="Phone number must be a valid UK number with only digits (e.g., '07123456789' or '02012345678')"
            )
        ]
    )  # Contact phone number
    email = models.EmailField(
        max_length=320,
        validators=[
            RegexValidator(
                r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                message="Please enter a valid email address"
            )
        ]
    )  # Contact email address
    address_line1 = models.CharField(
        max_length=80,
        validators=[
            RegexValidator(
                r'^[A-Za-z0-9\-\',\. ]+$',
                message="Address can only contain letters, numbers, hyphens, apostrophes, commas, periods and spaces"
            )
        ]
    )  # Primary address line
    address_line2 = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                r'^[A-Za-z0-9\-\',\. ]+$',
                message="Address can only contain letters, numbers, hyphens, apostrophes, commas, periods and spaces"
            )
        ]
    )  # Secondary address line (optional)
    city = models.CharField(
        max_length=80,
        validators=[
            RegexValidator(
                r'^[A-Za-z\-\' ]+$',
                message="City can only contain letters, hyphens, apostrophes and spaces"
            )
        ]
    )  # City of residence
    county = models.CharField(
        max_length=80,
        validators=[
            RegexValidator(
                r'^[A-Za-z\-\' ]+$',
                message="County can only contain letters, hyphens, apostrophes and spaces"
            )
        ]
    )  # County/state/region
    postcode = models.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                r'^([A-Za-z][A-Ha-hJ-Yj-y]?\d[A-Za-z\d]? ?\d[A-Za-z]{2}|GIR ?0A{2})$',
                message="Please enter a valid UK postcode (e.g., 'SW1A 1AA', 'M1 1AA' or 'B338TH')"
            )
        ]
    )  # Postal/ZIP code

    def __str__(self):
        """
        Return a string representation of the guest.

        Returns:
            str: A string in the format 'ID:{id}: Full name:{title first_name last_name}'
                e.g., 'ID:123: Full name:Mr John Smith'
        """
        guest_str = f"ID:{self.guest_id}: Full name:{self.title} {self.first_name} {self.last_name}"
        logger.info(f"Guest __str__ called: {guest_str}")
        return guest_str

    @property
    def display_name(self):
        """
        Return a shorter formatted name for display purposes.

        Returns:
            str: A string in the format '{title} {first_initial}. {last_name}'
                e.g., 'Mr J. Smith'
        """
        display_name = f"{self.title} {self.first_name[0]}. {self.last_name}"
        logger.info(f"Guest display_name property called: {display_name}")
        return display_name


class RoomType(models.Model):
    """
    Model representing different types of hotel rooms and their characteristics.

    This model defines various room categories with their amenities, pricing,
    and capacity information. Each room type has a unique code and specific features
    that distinguish it from other types.
    """
    room_type_code = models.CharField(
        max_length=3,
        validators=[
            MinLengthValidator(1),
            RegexValidator(r'^[A-Z]{1,3}$', message="The room type code must be between 1 and 3 uppercase letters"),
        ],
        unique=True,
        primary_key=True,
        help_text="Unique 1-3 letter code for the room type (e.g., 'STD' for Standard)"
    )
    room_type_name = models.CharField(
        max_length=25,
        help_text="Descriptive name for the room type"
    )
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Nightly rate for this room type"
    )
    deluxe = models.BooleanField(
        help_text="Indicates if this is a deluxe category room"
    )
    bath = models.BooleanField(
        help_text="Indicates if the room has a bathtub"
    )
    separate_shower = models.BooleanField(
        help_text="Indicates if the room has a separate shower unit"
    )
    maximum_guests = models.PositiveSmallIntegerField(
        help_text="Maximum number of guests allowed in this room type"
    )

    def __str__(self):
        room_type_str = self.room_type_name
        logger.info(f"RoomType __str__ called: {room_type_str}")
        return room_type_str


class Room(models.Model):
    """
    Model representing individual hotel rooms.

    Each room has a unique room number and is associated with a specific room type
    that defines its characteristics and pricing. This model creates the link between
    physical rooms and their type specifications.
    """
    room_number = models.IntegerField(
        primary_key=True,
        unique=True,
        help_text="Unique identifier for the room (e.g., 101, 102, etc.)"
    )
    room_type = models.ForeignKey(
        RoomType,
        null=True,
        on_delete=models.SET_NULL,
        related_name="rooms",
        help_text="The type/category of this room, determining its features and price"
    )

    def __str__(self):
        room_str = f"{self.room_number}"
        logger.info(f"Room __str__ called: {room_str}")
        return room_str


class Reservation(models.Model):
    """
    Model representing hotel room reservations.

    This model tracks all aspects of a room booking including guest information,
    room details, dates, payment status, and booking status. It manages the complete
    lifecycle of a reservation from initial booking through check-out.
    """
    STATUS_CHOICES = [
        ("RE", "Reserved"),  # Initial reservation status
        ("IN", "Checked In"),  # Guest has arrived and checked in
        ("OT", "Checked Out"),  # Guest has completed their stay
    ]

    reservation_id = models.AutoField(
        primary_key=True,
        help_text="Unique identifier for the reservation"
    )
    guest = models.ForeignKey(
        Guest,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reservations",
        help_text="Guest making the reservation"
    )
    room_number = models.ForeignKey(
        Room,
        null=True,
        on_delete=models.SET_NULL,
        related_name="reservations",
        help_text="Room assigned to this reservation"
    )
    reservation_date_time = models.DateTimeField(
        help_text="Date and time when the reservation was made"
    )
    price = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Total price for the entire stay"
    )
    amount_paid = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Amount already paid by the guest"
    )
    number_of_guests = models.PositiveSmallIntegerField(
        help_text="Number of guests staying in the room"
    )
    start_of_stay = models.DateField(
        help_text="Check-in date"
    )
    length_of_stay = models.PositiveSmallIntegerField(
        help_text="Number of nights booked"
    )
    end_date = models.DateField(null=True, blank=True) # this will be derived from start_of_stay and length_of_stay during save()
    status_code = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        help_text="Current status of the reservation"
    )
    notes = models.TextField(
        max_length=500,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                r'^[A-Za-z0-9\-\',\.\!\?\s]+$',
                message="Notes can only contain letters, numbers, basic punctuation and spaces"
            )
        ],
        help_text="Additional notes or special requests for the reservation"
    )

    def clean(self):
        """
        Validate the reservation data.
        """
        cleaned_data = super().clean()

        # Validate number of guests against room capacity
        if self.room_number:
            validate_guest_count(self, self.room_number)

        # Validate payment amount
        validate_payment(self.amount_paid, self.price)

        # Validate booking time to check for an overlapping reservation
        self.validate_to_detect_overlapping_reservation()
    
    # Check that the reservation dates don't overlap an existing reservation
    def validate_to_detect_overlapping_reservation(self):
        if self.length_of_stay is None:
            self.length_of_stay = getattr(self, 'length_of_stay', None) 

        """ Prevent overlapping reservations for the same room. """
        overlapping_reservations = Reservation.objects.filter(
            room_number=self.room_number, # find other reservations using the same room
            start_of_stay__lt=(self.start_of_stay + timedelta(days=self.length_of_stay)),  # Existing booking starts before this one ends
            end_date__gt=self.start_of_stay  # Existing booking ends after this one starts
        ).exclude(pk=self.pk)  # Exclude our own record in case we're updating our existing reservation

        if overlapping_reservations.exists():
            raise ValidationError("This room is already booked for the entered dates.")


    def save(self, *args, **kwargs):
        #  Automatically calculate and store end_date before saving
        if self.start_of_stay and self.length_of_stay:
            self.end_date = self.start_of_stay + timedelta(days=self.length_of_stay)

        self.full_clean()  # Call full_clean before saving to force validation
        super().save(*args, **kwargs)

    def __str__(self):
        """
        Return a string representation of the reservation.

        Returns:
            str: A string in the format 'Reservation {id} - {status}'
                e.g., 'Reservation 123 - IN' for a checked-in reservation
        """
        reservation_str = f"Reservation {self.reservation_id} - {self.status_code}"
        logger.info(f"Reservation __str__ called: {reservation_str}")
        return reservation_str

    
  