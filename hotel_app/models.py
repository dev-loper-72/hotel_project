# django data models that will be used to create & maintain the database tables
# to store data entered by the user
from django.db import models
from django.db.models import F, ExpressionWrapper, IntegerField
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from datetime import timedelta

class Guest(models.Model):
    guest_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=10)
    first_name = models.CharField(max_length=50)
    last_name =  models.CharField(max_length=50)
    phone_number = models.CharField(max_length=11)
    email = models.EmailField(max_length=320)
    address_line1 = models.CharField(max_length=80)
    address_line2 = models.CharField(max_length=80, blank=True, null=True)
    city = models.CharField(max_length=80)
    county = models.CharField(max_length=80)
    postcode = models.CharField(max_length=8)

     # string representation of the Guest
    def __str__(self):
        return (f"ID:{self.guest_id}: Full name:{self.title + " " + self.first_name + " " + self.last_name}") 
    
    # shorter guest name built from the title + first_initial + last_name
    @property
    def display_name(self):
        return f"{self.title} {self.first_name[0]}. {self.last_name}" 


class RoomType(models.Model):
    room_type_code = models.CharField(
        max_length=3, 
        validators=[
            MinLengthValidator(1), 
            RegexValidator(r'^[A-Z]{1,3}$', message="The room type code must be between 1 and 3 uppercase letters"),
        ],
        unique=True, 
        primary_key=True,
    )
    room_type_name = models.CharField(max_length=25)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    deluxe = models.BooleanField()
    bath = models.BooleanField()
    separate_shower = models.BooleanField()
    maximum_guests = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.room_type_name


class Room(models.Model):
    room_number = models.IntegerField(primary_key=True, unique=True)
    room_type = models.ForeignKey(RoomType, null=True, on_delete=models.SET_NULL, related_name="rooms")

    def __str__(self):
        return f"{self.room_number}"


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("RE", "Reserved"),
        ("IN", "Checked In"),
        ("OT", "Checked Out"),
    ]

    reservation_id = models.AutoField(primary_key=True)
    guest = models.ForeignKey(Guest, null=True, on_delete=models.SET_NULL, related_name="reservations")
    room_number = models.ForeignKey(Room, null=True, on_delete=models.SET_NULL, related_name="reservations")
    reservation_date_time = models.DateTimeField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=6, decimal_places=2)
    number_of_guests = models.PositiveSmallIntegerField()
    start_of_stay = models.DateField()
    length_of_stay = models.PositiveSmallIntegerField()
    status_code = models.CharField(max_length=2, choices=STATUS_CHOICES)
    notes = models.TextField(max_length=500, blank=True, null=True)

    @property
    def end_date(self):
        # Calculate and return the end date by using start_of_stay and length_of_stay
        return self.start_of_stay + timedelta(days=self.length_of_stay)

    def clean(self):
        """ Prevent overlapping reservations for the same room. """
        overlapping_reservations = Reservation.objects.filter(
            room_number=self.room_number # find other reservations using the same room
        ).annotate(
            # Calculate if the other reservation's end date is before or after this one's start date
            # (uses /86400000000 to convert date to whole days as sqlite3 doesn't like the date+int arithmetic )
            # if days_between < 0 then the other reservation will ended after this one starts and so is considered a
            # potential overlapping reservation (other filters will need to be checked)
            days_between=ExpressionWrapper(
                ((F('start_of_stay') -self.start_of_stay)/86400000000)+ F('length_of_stay'), output_field=IntegerField() # convert to whole days
            )
        ).filter(
            start_of_stay__lt=self.end_date,  # Existing booking starts before this one ends
            days_between__gt=0  # Existing booking ends after this one starts
        ).exclude(pk=self.pk)  # Exclude our own record in case we're updating our existing reservation


        if overlapping_reservations.exists():
            raise ValidationError("This room is already booked for the entered dates.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Call full_clean before saving to force validation
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reservation {self.reservation_id} - {self.status_code}"
