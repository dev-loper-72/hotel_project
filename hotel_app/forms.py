"""
Django forms for use on HTML pages to link to the data model.

This module defines various forms used in the hotel management application,
including forms for user authentication, guest management, room management,
and reservation management.
"""

import logging
import re
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Guest, Room, RoomType, Reservation
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError


# create a Logger for use anywhere in this code and configure it to write info messages (or higher) to the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The form for the Login page
class LoginForm(AuthenticationForm):
    """
    Form for the Login page.

    This form handles user authentication by collecting the username and password.
    """
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean(self):
        """
        Override clean method to add authentication logging.
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            logger.info(f"Authenticating user: {username}")
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                logger.warning(f"Invalid login attempt for user: {username}")
                raise ValidationError('Invalid username or password', code='invalid_login')
            logger.info(f"User {username} authenticated successfully")
        return self.cleaned_data

# The form for the Guest editor 
class GuestForm(forms.ModelForm):
    """
    Form for the Guest editor.

    This form allows for the creation and editing of guest information, including
    personal details and contact information.
    """
    def clean_phone_number(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone_number')
        if not phone:
            return phone

        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits")
        if not (phone.startswith('07') or phone.startswith('0')):
            raise forms.ValidationError("Phone number must start with '07' for mobile or '0' for landline")
        if len(phone) != 11:
            raise forms.ValidationError("Phone number must be 11 digits long")
        return phone

    def clean_postcode(self):
        """Validate UK postcode format."""
        postcode = self.cleaned_data.get('postcode')
        if not postcode:
            return postcode

        # Convert to uppercase and remove spaces for validation
        postcode = postcode.upper().strip()

        # UK postcode regex pattern
        pattern = r'^([A-Z]{1,2}[0-9][A-Z0-9]? ?[0-9][A-Z]{2})$'

        if not re.match(pattern, postcode):
            raise forms.ValidationError("Please enter a valid UK postcode (e.g., 'SW1A 1AA' or 'M1 1AA')")
        return postcode

    def clean(self):
        """
        Override clean method to add guest form validation logging.
        """
        cleaned_data = super().clean()
        if not self.errors:
            logger.info(f"Validating guest form data for {cleaned_data.get('first_name')} {cleaned_data.get('last_name')}")
            # Combine names for display_name
            cleaned_data['display_name'] = (
                f"{cleaned_data['first_name']} {cleaned_data['last_name']}"
            )
        else:
            logger.warning("Guest form validation failed")
            logger.info(f"Form errors: {self.errors}")
        return cleaned_data

    # Define choices for the title field
    TITLE_CHOICES = [
        ('Mr', 'Mr'),
        ('Miss', 'Miss'),
        ('Mrs', 'Mrs'),
        ('Ms', 'Ms'),
        ('Dr', 'Dr'),
        ('Prof', 'Prof'),
        ('Sir', 'Sir'),
        ('Dame', 'Dame'),
        (' ', ' '),
    ]

    title = forms.ChoiceField(choices=TITLE_CHOICES, required=True)
    first_name = forms.CharField(max_length=50)
    last_name =  forms.CharField(max_length=50)
    phone_number =  forms.CharField(max_length=11)
    email =  forms.CharField(max_length=320)
    address_line1 =  forms.CharField(max_length=80)
    address_line2 =  forms.CharField(max_length=80, required=False)
    city =  forms.CharField(max_length=80)
    county =  forms.CharField(max_length=80)
    postcode =  forms.CharField(max_length=8)
    class Meta:
        model = Guest
        labels = {
            'guest_id': 'Guest ID',
            'title': 'Title',
            'first_name': 'First name',
            'last_name': 'Last name',
            'phone_number': 'Phone Number',
            'email': 'Email Address',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'city': 'City',
            'county': 'County',
            'postcode': 'Postcode',
        }
        fields = [
            'guest_id', 'title', 'first_name', 'last_name',
            'phone_number', 'email', 'address_line1', 'address_line2',
            'city', 'county', 'postcode',
        ]
        widgets = {
            'guest_id': forms.NumberInput(
                attrs={'placeholder':'e.g. 1', 'class':'form-control'}),
            'title': forms.TextInput(
                attrs={'placeholder':'e.g. Mr', 'class':'form-control'}),
            'first_name': forms.TextInput(
                attrs={'class':'form-control'}),
            'last_name': forms.TextInput(
                attrs={'placeholder':'e.g. Smith', 'class':'form-control'}),
            'phone_number': forms.TextInput(
                attrs={'placeholder': 'Phone Number', 'class': 'form-control'}),
            'email': forms.EmailInput(
                attrs={'placeholder': 'Email Address', 'class': 'form-control'}),
            'address_line1': forms.TextInput(
                attrs={'class': 'form-control'}),
            'address_line2': forms.TextInput(
                attrs={'required': False, 'placeholder': 'Address Line 2', 'class': 'form-control'}),
            'city': forms.TextInput(
                attrs={'placeholder': 'City', 'class': 'form-control'}),
            'county': forms.TextInput(
                attrs={'placeholder': 'County', 'class': 'form-control'}),
            'postcode': forms.TextInput(
                attrs={'placeholder': 'Postcode', 'class': 'form-control'}),                
        }

# The form for the Reservation editor 
class ReservationForm(forms.ModelForm):
    """
    Form for the Reservation editor.

    This form handles the creation and editing of reservations, including details
    such as guest information, room details, stay duration, and payment status.
    """
    # some fields need to be read-only and their values will be
    # preset by the view based on selections made on previous pages
    # e.g. the chosen guest for the reservation, the room, the  
    #      start date of the stay and the length of stay
     
    class Meta:
        model = Reservation
        fields = [
            'guest_display', 'room_number_display',             
            'start_of_stay', 'length_of_stay',
            'reservation_date_time', 'status_code',
            'number_of_guests',
            'price', 'amount_paid',
            'notes'
        ]  # Explicitly defining the order of fields        
    
    # Customising the fields
    guest_display = forms.CharField( # display only version of the guest - this avoids retrieving ALL guests into a ChoiceField
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'disabled': 'disabled'}),
        label="Guest"
    )
    room_number_display = forms.CharField( # display only version of the room - this avoids retrieving ALL rooms into a ChoiceField
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'disabled': 'disabled'}),
        label="Room"
    )
    reservation_date_time = forms.DateTimeField( # date & time the reservation was created in UK format
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'placeholder': 'dd/mm/yyyy HH:MM:SS', 'readonly': 'readonly', 'disabled': 'disabled'}, format='%d/%m/%Y %H:%M:%S'),
        label="Reservation Date/Time"
    )
    start_of_stay = forms.DateField( # date of the first night guest will be occupying the room (in UK format)
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'dd/mm/yyyy', 'readonly': 'readonly', 'disabled': 'disabled'}, format='%d/%m/%Y'),
        label="Date of Stay"
    )
    length_of_stay = forms.IntegerField( # the number of nights the guest will be occupying the room
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'disabled': 'disabled'}),
        label="Number of Nights"
    )
    price = forms.DecimalField( # the price of the reservation (room price * length of stay)
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'disabled': 'disabled'}),
        label="Total Price",
    )
    amount_paid = forms.DecimalField( # the amount paid by the guest so far (deposit etc)
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01', 'type': 'number'}),
        label="Amount Paid",
        max_digits=6,
        decimal_places=2,
    )
    number_of_guests = forms.IntegerField( # the number of guests staying in the room
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'type': 'number'}),
        label="Number of Guests"
    )
    status_code = forms.ChoiceField( # the status of the room (Reserved / Checked-in / Checked-out )
        required=False, 
        choices=Reservation.STATUS_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control', 'readonly': 'readonly', 'disabled': 'disabled'}),
        label="Occupancy Status"
    )
    notes = forms.CharField( # optional notes that can be made by the Receptionist
        required=False, 
        widget=forms.Textarea(attrs={'class': 'form-control'}),
        label="Notes"
    )

    # Override clean to make sure the read-only values are also saved into the model
    # so they can be used for validation
    # Note: by default django seem to put read-only/disabled values in the cleaned_data
    # so this seems a necessary step for validation
    def clean(self):
        """
        Validate the reservation data.
        """
        cleaned_data = super().clean()

        if cleaned_data.get('guest') is None:
            cleaned_data['guest'] = self.initial.get('guest')
        if cleaned_data.get('room_number') is None:
            cleaned_data['room_number'] = self.initial.get('room_number')
        if cleaned_data.get('reservation_date_time') is None:
            cleaned_data['reservation_date_time'] = self.initial.get('reservation_date_time')
        if cleaned_data.get('start_of_stay') is None:
            cleaned_data['start_of_stay'] = self.initial.get('start_of_stay')
        if cleaned_data.get('length_of_stay') is None:
            cleaned_data['length_of_stay'] = self.initial.get('length_of_stay')
        if cleaned_data.get('price') is None:
            cleaned_data['price'] = self.initial.get('price')
        if cleaned_data.get('status_code') is None:
            cleaned_data['status_code'] = self.initial.get('status_code')

        # Validate number of guests
        number_of_guests = cleaned_data.get('number_of_guests')
        room_number = self.initial.get('room_number') or (self.instance and self.instance.room_number)

        if number_of_guests and room_number:
            if number_of_guests < 1:
                self.add_error('number_of_guests', "Number of guests must be at least 1")
            if number_of_guests > room_number.room_type.maximum_guests:
                self.add_error('number_of_guests',
                    f"Maximum number of guests for this room is {room_number.room_type.maximum_guests}"
                )

        # Validate payment amount
        amount_paid = cleaned_data.get('amount_paid')
        price = cleaned_data.get('price') or self.initial.get('price')

        if amount_paid is not None and price is not None:
            if amount_paid < 0:
                self.add_error('amount_paid', "Payment amount must be 0 or greater")
            if amount_paid > price:
                self.add_error('amount_paid', f"Payment amount cannot exceed the total price of {price}")

        return cleaned_data

    def save(self, commit=True):
        """
        Override save to ensure read-only values are also saved into the model.

        By default, Django doesn't save read-only/disabled values, so this method
        manually updates the instance values of non-editable fields if they are empty
        and the initial data has been provided.

        Args:
            commit (bool): Whether to commit the save to the database.

        Returns:
            instance: The saved instance of the reservation.
        """
        instance = super().save(commit=False)
        
        # Log all field values in the instance being saved
        logger.info("Reservation Form save")
        for field in instance._meta.fields:
            field_name = field.name
            field_value = getattr(instance, field_name, None)  # Get field value safely
            logger.info(f" - {field_name}: {field_value!r}")  # !r to show raw values            
        
        # Manually update the instance values of non-editable fields if the instance values are empty and 
        # the initial data has been provided (e.g. Create mode)
        instance.guest = getattr(instance, 'guest', None) or self.initial.get('guest')
        instance.room_number = getattr(instance, 'room_number', None) or self.initial.get('room_number')
        instance.reservation_date_time = getattr(instance, 'reservation_date_time', None) or self.initial.get('reservation_date_time')
        instance.start_of_stay = getattr(instance, 'start_of_stay', None) or self.initial.get('start_of_stay')
        instance.length_of_stay = getattr(instance, 'length_of_stay', None) or self.initial.get('length_of_stay')
        instance.price = getattr(instance, 'price', None) or self.initial.get('price')
        instance.status_code = getattr(instance, 'status_code', None) or self.initial.get('status_code')

        if commit:
            instance.save()
        return instance


    # initialise
    def __init__(self, *args, **kwargs):
        """
        Initialize the ReservationForm with initial data and instance data.

        This method populates the 'display only' versions of the guest and room
        fields based on the provided initial data or instance data.

        Args:
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(*args, **kwargs)
        
        # Check if initial data has been provided
        initial_data = kwargs.get('initial', {})

        # Check if an instance is provided (for editing an existing reservation)
        instance = kwargs.get('instance', None)

        # populate the 'display only' version of the guest
        if "guest" in initial_data:
            guest = initial_data["guest"]
        elif instance and instance.guest:  # use instance data if initial is not set
            guest = instance.guest
        else:
            guest = None

        if guest:
            self.fields['guest_display'].initial = guest.display_name  

        # populate the 'display only' version of the room
        if "room_number" in initial_data:
            room_number = initial_data["room_number"]
        elif instance and instance.room_number:  # Use instance data if initial is not set
            room_number = instance.room_number
        else:
            room_number = None

        if room_number:
            self.fields['room_number_display'].initial = room_number



class RoomForm(forms.ModelForm):
    """
    Form for the Room editor.

    This form allows for the creation and editing of room information, including
    the room number and room type.
    """
    def clean(self):
        """
        Override clean method to add room form validation logging.
        """
        cleaned_data = super().clean()
        if not self.errors:
            room_number = cleaned_data.get('room_number')
            room_type = cleaned_data.get('room_type')
            logger.info(f"Validating room form - Number: {room_number}, Type: {room_type}")

            if not self.instance.pk and Room.objects.filter(room_number=room_number).exists():
                logger.warning(f"Attempted to create room with existing number: {room_number}")
                raise ValidationError('Room number already exists')
        else:
            logger.warning("Room form validation failed")
            logger.info(f"Form errors: {self.errors}")
        return cleaned_data
    room_number = forms.NumberInput()
    room_type = forms.ModelChoiceField(queryset=RoomType.objects.all(), label='Room Type', required=True)
    class Meta:
        model = Room
        labels = {
            'room_number': 'Room Number',
            'room_type': 'Room Type',
        }
        fields = [
            'room_number', 'room_type',
        ]

class RoomTypeForm(forms.ModelForm):
    """
    Form for the Room Type editor.

    This form allows for the creation and editing of room type information, including
    the room type code, name, pricing, and various amenities.
    """
    def clean(self):
        """
        Override clean method to add room type form validation logging.
        """
        cleaned_data = super().clean()
        if not self.errors:
            room_type_code = cleaned_data.get('room_type_code')
            room_type_name = cleaned_data.get('room_type_name')
            price = cleaned_data.get('price')
            logger.info(f"Validating room type form - Code: {room_type_code}, "
                       f"Name: {room_type_name}, Price: {price}")
        else:
            logger.warning("Room type form validation failed")
            logger.info(f"Form errors: {self.errors}")
        return cleaned_data
    
    room_type_code = forms.CharField(max_length=3)
    room_type_name = forms.CharField(max_length=50)
    price =  forms.NumberInput()
    deluxe =  forms.CheckboxInput()
    bath =  forms.CheckboxInput()
    separate_shower =  forms.CheckboxInput()
    maximum_guests =  forms.NumberInput()
    class Meta:
        model = RoomType
        fields = [
            'room_type_code', 'room_type_name', 'price', 'deluxe',
            'bath', 'separate_shower', 'maximum_guests', 
        ]
        widgets = {
            'room_type_code': forms.TextInput(attrs={'placeholder': 'Code (e.g., SI, DO)', 'class': 'form-control'}),
            'room_type_name': forms.TextInput(attrs={'placeholder': 'Room Type Name (e.g., Suite)', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'placeholder': 'Price', 'class': 'form-control', 'step': '0.50'}),
            'deluxe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'bath': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'separate_shower': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'maximum_guests': forms.NumberInput(attrs={'placeholder': 'Maximum Guests', 'class': 'form-control', 'min': 1}),
        }
        labels = {
            'room_type_code': 'Room Type Code',
            'room_type_name': 'Room Type Name',
            'price': 'Price (per night)',
            'deluxe': 'Deluxe',
            'bath': 'Has Bath',
            'separate_shower': 'Separate Shower',
            'maximum_guests': 'Maximum Guests',
        }

    # # helper function to validate the room type code
    # def clean_room_type_code(self):
    #     """Validate the room type code."""
    #     room_type_code = self.cleaned_data['room_type_code']
    #     if len(room_type_code) != 2:
    #         raise forms.ValidationError("Room Type Code must contain exactly two characters.")
    #     return room_type_code.upper()

    # # helper function to validate the room type name    
    