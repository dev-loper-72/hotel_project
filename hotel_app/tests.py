from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils.timezone import make_aware
from datetime import datetime, date
from .models import Guest, RoomType, Room, Reservation
from .forms import RoomTypeForm

#
# Ideas for extra validation in the model and extra tests 
#
# Guest:
#
#     Validation: Limit phone_number to numeric only
#                 Apply a RegEx format to postcode 
#     Test:       Test validation above
#                 Test trying to exceed character limits for each field
#                 Test using None for each not null field
#                 Test Update and Delete
#
# Room Type:
#
#     Validation: Check price > 0 and below a sensible value, e.g.  < 1000
#                 Check maximum_guests > 0 and below a sensible value, e.g.  < 12
#     Test:       Test validation above
#                 Test trying to exceed character limits for each field
#                 Test using None for each not null field
#                 Test Update and Delete
#
# Room:
#
#     Test:       Test creating two rooms with the same room_number
#                 Test creating a room without specifying the room_type
#                 Test using None for each not null field
#                 Test Update and Delete
#                 
# Reservation:
#
#     Validation: Check number_of_guests <= the maximum_guests of the chosen room_number
#                 Check reservation_date_time is within a sensible range (e.g. from 1st Feb 2025 to 31st Dec 2035)
#                 Same for start_of_stay
#                 Check length_of_stay > 0 and <= 365 days
#                 Check amount_paid >= 0 and <= price
#     Test:       Test validation above
#                 Test trying to exceed character limits for each field
#                 Test using None for each not null field
#                 Test Update and Delete
#
#
# Forms.... (Room Type has been tested, but do the same for Guest/Room/Reservation)
#
# View.... check navigation works as expected

# Test the data models
class TestGuestModel(TestCase):
    def test_guest_creation(self):
        guest1 = Guest.objects.create(
            title = 'Mr',
            first_name = 'John',
            last_name =  'Smith',
            phone_number = '07977123456',
            email = 'j.smith@gmail.com',
            address_line1 = '1 The Street',
            address_line2 = 'Test Town',
            city = 'Test City',
            county = 'Test County',
            postcode = 'IP128AB')
        
        try:
            guest1.full_clean()  # Call the full_clean method to validate
        except ValidationError:
            self.fail("full_clean() raised a ValidationError")

        # Confirm guest was saved
        self.assertEqual(Guest.objects.count(), 1)

        # Verify the guest details
        saved_guest = Guest.objects.get(guest_id=guest1.guest_id)
        self.assertEqual(saved_guest.first_name, 'John')
        self.assertEqual(saved_guest.last_name, 'Smith')
        self.assertEqual(saved_guest.phone_number, '07977123456')
        self.assertEqual(saved_guest.email, 'j.smith@gmail.com')
        self.assertEqual(saved_guest.address_line1, '1 The Street')
        self.assertEqual(saved_guest.address_line2, 'Test Town')
        self.assertEqual(saved_guest.city, 'Test City')
        self.assertEqual(saved_guest.county, 'Test County')
        self.assertEqual(saved_guest.postcode, 'IP128AB')

    def test_guest_creation_null_values(self):
        # check the missing values causes an integrity error
        with self.assertRaises(IntegrityError):
            guest1 = Guest.objects.create(
                title = 'Mr',
                first_name = 'John',
                last_name =  'Smith',
                phone_number = None, # required value missing 
                email = 'j.smith@gmail.com',
                address_line1 = None, # required value missing 
                address_line2 = 'Test Town',
                city = 'Test City',
                county = 'Test County',
                postcode = 'IP128AB')
        
class TestRoomTypeModel(TestCase):
    def test_room_type_creation(self):
        roomType1 = RoomType.objects.create(
            room_type_code = 'DO',
            room_type_name = 'Double',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 2
        )
        
        try:
            roomType1.full_clean()  # Call the full_clean method to validate
        except ValidationError:
            self.fail("full_clean() raised a ValidationError")

        # Confirm room_type was saved
        self.assertEqual(RoomType.objects.count(), 1)

        # Verify the room type details
        saved_roomType = RoomType.objects.get(room_type_code=roomType1.room_type_code)
        self.assertEqual(saved_roomType.room_type_code, 'DO')
        self.assertEqual(saved_roomType.room_type_name, 'Double')
        self.assertEqual(saved_roomType.price, 80.0)
        self.assertEqual(saved_roomType.deluxe, False)
        self.assertEqual(saved_roomType.bath, False)
        self.assertEqual(saved_roomType.separate_shower, True)
        self.assertEqual(saved_roomType.maximum_guests, 2)

    def test_room_type_creation_invalid_room_type_code(self):
        roomType1 = RoomType.objects.create(
            room_type_code = 'S*I',
            room_type_name = 'Single',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 1
        )
        
        # Check that full clean raises a ValidationError for the invalid room_type
        with self.assertRaises(ValidationError):
            roomType1.full_clean()  # Call the full_clean method to validate

    def test_room_type_creation_duplicate_room_type_code(self):
        # create the room
        roomType1 = RoomType.objects.create(
            room_type_code = 'SI',
            room_type_name = 'Single',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 1
        )

        # try to create a duplicate room_type_code
        with self.assertRaises(IntegrityError):
            # Use transaction.atomic to isolate the failing query so that the test can continue
            with transaction.atomic():  
                roomType2 = RoomType.objects.create(
                    room_type_code = 'SI',
                    room_type_name = 'Single Deluxe',
                    price = 85.0,
                    deluxe = True,
                    bath = True,
                    separate_shower = False,
                    maximum_guests = 1
                )
        
        # now correct the room_type_code and try again
        roomType2 = RoomType.objects.create(
                room_type_code = 'SID',
                room_type_name = 'Single Deluxe',
                price = 85.0,
                deluxe = True,
                bath = True,
                separate_shower = False,
                maximum_guests = 1
            )

        # Confirm room_type was saved, making the count = 2
        self.assertEqual(RoomType.objects.count(), 2)

class TestRoomModel(TestCase):
    def setUp(self):
        #Set up before each test
        # create some room types that can be assigned to a room
        self.roomType_single = RoomType.objects.create(
            room_type_code = 'SI',
            room_type_name = 'Single',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 1
        )
        self.roomType_double = RoomType.objects.create(
            room_type_code = 'DO',
            room_type_name = 'Double',
            price = 105.0,
            deluxe = False,
            bath = True,
            separate_shower = True,
            maximum_guests = 2
        )

    def test_room_creation(self):
        room1 = Room.objects.create(
            room_number = 5,
            room_type = self.roomType_single
        )
        
        try:
            room1.full_clean()  # Call the full_clean method to validate
        except ValidationError:
            self.fail("full_clean() raised a ValidationError")

        # Confirm room_type was saved
        self.assertEqual(Room.objects.count(), 1)

        # Verify the room type details
        saved_room = Room.objects.get(room_number=5)
        self.assertEqual(saved_room.room_number, 5)
        self.assertEqual(saved_room.room_type, self.roomType_single)

class TestReservationModel(TestCase):
    def setUp(self):
        #Set up before each test
        # create a room type, two rooms and two guests
        self.roomType_single = RoomType.objects.create(
            room_type_code = 'SI',
            room_type_name = 'Single',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 1
        )
        self.room1 = Room.objects.create(
            room_number = 1,
            room_type = self.roomType_single
        )
        self.room2 = Room.objects.create(
            room_number = 2,
            room_type = self.roomType_single
        )
        self.guest1 = Guest.objects.create(
            title = 'Mr',
            first_name = 'John',
            last_name =  'Smith',
            phone_number = '07977123456',
            email = 'j.smith@gmail.com',
            address_line1 = '1 The Street',
            address_line2 = 'Test Town',
            city = 'Test City',
            county = 'Test County',
            postcode = 'IP128AB')
        self.guest2 = Guest.objects.create(
            title = 'Miss',
            first_name = 'Emily',
            last_name =  'Brown',
            phone_number = '01473600000',
            email = 'e.brown@outlook.com',
            address_line1 = '18 River Lane',
            address_line2 = None,
            city = 'Norwich',
            county = 'Norfolk',
            postcode = 'NR11JP')
        
        

    def test_reservation_creation(self):
        res1 = Reservation.objects.create(
            guest = self.guest1,
            room_number = self.room1,
            reservation_date_time = make_aware(datetime(2025, 2, 21, 14, 30)),
            price = self.room1.room_type.price, # set to the room price at the time of booking
            amount_paid=0.0,
            number_of_guests=1,
            start_of_stay=date(2025, 2, 23), # room will be occupied for the nights 23rd Feb to 25th Feb incl.
            length_of_stay=3,
            status_code='RE',  # Reserved
            notes='Requested late check-in.'
        )
        
        try:
            res1.full_clean()  # Call the full_clean method to validate
        except ValidationError:
            self.fail("full_clean() raised a ValidationError")

        # Confirm reservation was saved
        self.assertEqual(Reservation.objects.count(), 1)

        # Verify the room type details
        saved_reservation = Reservation.objects.get(reservation_id = res1.reservation_id)
        self.assertEqual(saved_reservation.reservation_id, res1.reservation_id)
        self.assertEqual(saved_reservation.guest, self.guest1)
        self.assertEqual(saved_reservation.room_number, self.room1)
        expected_datetime = make_aware(datetime(2025, 2, 21, 14, 30))  # Convert to timezone-aware
        self.assertEqual(saved_reservation.reservation_date_time, expected_datetime)
        self.assertEqual(saved_reservation.price, self.room1.room_type.price)
        self.assertEqual(saved_reservation.amount_paid, 0.0)
        self.assertEqual(saved_reservation.number_of_guests, 1)
        self.assertEqual(saved_reservation.start_of_stay, date(2025, 2, 23))
        self.assertEqual(saved_reservation.length_of_stay, 3)
        self.assertEqual(saved_reservation.status_code, 'RE')
        self.assertEqual(saved_reservation.notes, 'Requested late check-in.')

    def test_reservation_double_booking(self):
        res1 = Reservation.objects.create(
            guest = self.guest1,
            room_number = self.room1,
            reservation_date_time = make_aware(datetime(2025, 2, 21, 14, 30)),
            price = self.room1.room_type.price, # set to the room price at the time of booking
            amount_paid=0.0,
            number_of_guests=1,
            start_of_stay=date(2025, 2, 23),
            length_of_stay=3,
            status_code='RE',  # Reserved
            notes='Requested late check-in.'
        )
                
        # check that trying to create an overlapping booking is caught with a ValidationError
        # (overlapping the start of res1) 
        with self.assertRaises(ValidationError):
            res2 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room1,
                reservation_date_time = make_aware(datetime(2025, 2, 21, 17, 35)),
                price = self.room1.room_type.price, # set to the room price at the time of booking
                amount_paid=10.0,
                number_of_guests=1,
                start_of_stay=date(2025, 2, 22),
                length_of_stay=2,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (overlapping the end of res1)
        with self.assertRaises(ValidationError):
            res3 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room1,
                reservation_date_time = make_aware(datetime(2025, 2, 21, 17, 35)),
                price = self.room1.room_type.price, # set to the room price at the time of booking
                amount_paid=10.0,
                number_of_guests=1,
                start_of_stay=date(2025, 2, 25),
                length_of_stay=1,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (starting before res1 and finishing after) 
        with self.assertRaises(ValidationError):
            res4 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room1,
                reservation_date_time = make_aware(datetime(2025, 2, 21, 17, 35)),
                price = self.room1.room_type.price, # set to the room price at the time of booking
                amount_paid=10.0,
                number_of_guests=1,
                start_of_stay=date(2025, 2, 22),
                length_of_stay=7,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (start and ends times inside the booking of res1) 
        res5 = Reservation.objects.create(
            guest = self.guest2,
            room_number = self.room1,
            reservation_date_time = make_aware(datetime(2025, 2, 21, 17, 35)),
            price = self.room1.room_type.price, # set to the room price at the time of booking
            amount_paid=15.0,
            number_of_guests=1,
            start_of_stay=date(2025, 2, 22),
            length_of_stay=1,
            status_code='RE',  # Reserved
            notes=None
        )

        # now create two valid bookings, one ending on the same day res1 starts
        res6 = Reservation.objects.create(
            guest = self.guest2,
            room_number = self.room1,
            reservation_date_time = make_aware(datetime(2025, 2, 21, 17, 35)),
            price = self.room1.room_type.price, # set to the room price at the time of booking
            amount_paid=20.0,
            number_of_guests=1,
            start_of_stay=date(2025, 2, 26),
            length_of_stay=1,
            status_code='RE',  # Reserved
            notes=None
        )            

        # Confirm the reservations were saved, should now have 3
        self.assertEqual(Reservation.objects.count(), 3)

# Test the forms
class RoomTypeFormTest(TestCase):

    def test_valid_form(self):
        #Test if the form is valid when using valid data
        form_data = {
            'room_type_code': 'DOD',
            'room_type_name': 'Double Deluxe',
            'price': 125.00,
            'deluxe': True,
            'bath': True,
            'separate_shower': False,
            'maximum_guests': 4
        }
        form = RoomTypeForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        #Test form validation when required fields are missing
        form_data = {
            'room_type_code': None,
            'room_type_name': None,
            'price': None,
            'deluxe': False,
            'bath': False,
            'separate_shower': False,
            'maximum_guests': None
        }
        form = RoomTypeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('room_type_code', form.errors)
        self.assertIn('room_type_name', form.errors)
        self.assertIn('price', form.errors)
        self.assertIn('maximum_guests', form.errors)

    def test_invalid_data(self):
        #Test form validation for fields that could be left empty or contain incorrect data types
        form_data = {
            'room_type_code': '',
            'room_type_name': '',
            'price': 'invalid_price',  # Should be a number
            'deluxe': False, # Checkbox fields, can only be True/False anyway
            'bath': False,
            'separate_shower': False,
            'maximum_guests': 'five'  # Should be an number
        }
        form = RoomTypeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('room_type_code', form.errors)
        self.assertIn('room_type_name', form.errors)
        self.assertIn('price', form.errors)
        self.assertIn('maximum_guests', form.errors)


# Test navigation between views
class TestViewNavigation(TestCase):
    def setUp(self):
        self.client = Client()

        # create a user and login
        self.user = User.objects.create_user(username='test_user', password='password')
        self.client.login(username='test_user', password='password')

        # create some data for viewing
        # Create John Smith as a new guest
        self.guest_smith = Guest.objects.create(
            title = 'Mr',
            first_name = 'John',
            last_name =  'Smith',
            phone_number = '07977123456',
            email = 'j.smith@gmail.com',
            address_line1 = '1 The Street',
            address_line2 = 'Test Town',
            city = 'Test City',
            county = 'Test County',
            postcode = 'IP128AB')        
        # Create a double room type
        self.roomType_double = RoomType.objects.create(
            room_type_code = 'DO',
            room_type_name = 'Double',
            price = 80.0,
            deluxe = False,
            bath = False,
            separate_shower = True,
            maximum_guests = 2
        )
        # Create a rooms 5 & 6 as doubles
        self.room5 = Room.objects.create(
            room_number = 5,
            room_type = self.roomType_double
        )
        self.room6 = Room.objects.create(
            room_number = 6,
            room_type = self.roomType_double
        )
        # Create a reservation for room 5
        res1 = Reservation.objects.create(
            guest = self.guest_smith,
            room_number = self.room5,
            reservation_date_time = make_aware(datetime(2025, 2, 21, 14, 30)),
            price = self.room5.room_type.price, # set to the room price at the time of booking
            amount_paid=0.0,
            number_of_guests=1,
            start_of_stay=date(2025, 2, 23),
            length_of_stay=3,
            status_code='RE',
            notes=''
        )

        # urls
        self.home_url = reverse('home')
        self.login_url = reverse('login')
        self.guest_list_url = reverse('guest_list')
        self.guest_create_url = reverse('guest_create')
        
    def test_home(self):
        # request the home page
        response = self.client.get(self.home_url)

		# checks the page response was successful and has used the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_guests_list(self):
        # request the guest list
        response = self.client.get(self.guest_list_url)
        
		# checks the page response was successful and has used the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_list.html')   
        self.assertContains(response, "John") # checks that John is in the guest list
        self.assertContains(response, "Smith") # checks that Smith is in the guest list     

    def test_guests_list_not_logged_in(self):
        # checks that requesting the guests list while logged out results in an error
        self.client.logout()

        response = self.client.get(self.guest_list_url)

        self.assertEqual(response.status_code, 302)
        # checks that the user is redirected to the login page
        self.assertTrue(response.url.startswith(self.login_url))

    def test_guest_delete_request(self):
        delete_url = reverse("guest_delete", args=[self.guest_smith.guest_id])
        # Verify the guest exists before deletion
        self.assertEqual(Guest.objects.count(), 1)
        # request the deletion page (will ask for confirmation)
        response = self.client.get(delete_url)
        # checks the page response was successful and has used the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_confirm_delete.html')   
        # confirm the deletion by submitting the form on the page
        response = self.client.post(delete_url, follow=True)  

        self.assertEqual(response.status_code, 200)  # Check successful response
        self.assertEqual(Guest.objects.count(), 0)  # Ensure guest has been deleted
        self.assertTemplateUsed(response, 'guest_list.html') # check that navigation has returned to the guest list page 



        
