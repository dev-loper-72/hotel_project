# django forms for use on html pages to link to the data model

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Guest, Room, RoomType, Reservation
import logging

# create a Logger for use anywhere in this code and configure it to write info messages (or higher) to the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The form for the Login page
class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

# The form for the Guest editor 
class GuestForm(forms.ModelForm):

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
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        label="Amount Paid",
        max_digits=6,  
        decimal_places=2,
    )
    number_of_guests = forms.IntegerField( # the number of guests staying in the room
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
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

    # override save to make sure the read-only values are also saved into the model
    # Note: by default django doesn't save read-only/disabled values so this is necessary
    #       to populate the database table
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Log all field values in the instance being saved
        logger.info(f"Reservation Form save")
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
        instance.status_code = getattr(instance, 'prstatus_codeice', None) or self.initial.get('status_code')

        if commit:
            instance.save()
        return instance


    # initialise
    def __init__(self, *args, **kwargs):        
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