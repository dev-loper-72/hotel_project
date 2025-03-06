from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import IntegrityError, transaction
from datetime import date, timedelta
from decimal import Decimal
from hotel_app.models import Guest, RoomType, Room, Reservation

class GuestModelTest(TestCase):
    def setUp(self):
        self.valid_guest_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone_number': '07123456789',
            'email': 'john.smith@example.com',
            'address_line1': '123 Main Street',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }
        self.guest = Guest.objects.create(**self.valid_guest_data)

    def test_guest_creation(self):
        self.assertEqual(self.guest.first_name, 'John')
        self.assertEqual(self.guest.last_name, 'Smith')

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
            
    def test_guest_str_method(self):
        expected_str = f"ID:{self.guest.guest_id}: Full name:Mr John Smith"
        self.assertEqual(str(self.guest), expected_str)

    def test_guest_display_name(self):
        self.assertEqual(self.guest.display_name, "Mr J. Smith")

    def test_invalid_title(self):
        with self.assertRaises(ValidationError):
            guest = Guest(
                **{**self.valid_guest_data, 'title': 'Invalid'}
            )
            guest.full_clean()

    def test_invalid_phone_number(self):
        with self.assertRaises(ValidationError):
            guest = Guest(
                **{**self.valid_guest_data, 'phone_number': '12345'}
            )
            guest.full_clean()

class RoomTypeModelTest(TestCase):
    def setUp(self):
        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )

    def test_room_type_creation(self):
        self.assertEqual(self.room_type.room_type_code, 'STD')
        self.assertEqual(self.room_type.room_type_name, 'Standard Room')
        self.assertEqual(self.room_type.price, Decimal('100.00'))

    def test_room_type_str_method(self):
        self.assertEqual(str(self.room_type), 'Standard Room')

    def test_invalid_room_type_code(self):
        with self.assertRaises(ValidationError):
            room_type = RoomType(
                room_type_code='123',  # Should be letters only
                room_type_name='Test Room',
                price=Decimal('100.00'),
                deluxe=False,
                bath=True,
                separate_shower=False,
                maximum_guests=2
            )
            room_type.full_clean()

    def test_room_type_creation_duplicate_room_type_code(self):
        # try to create a duplicate room_type_code
        with self.assertRaises(IntegrityError):
            # Use transaction.atomic to isolate the failing query so that the test can continue
            with transaction.atomic():  
                roomType2 = RoomType.objects.create(
                    room_type_code='STD',
                    room_type_name='Deluxe Room',
                    price=Decimal('110.00'),
                    deluxe=True,
                    bath=True,
                    separate_shower=False,
                    maximum_guests=2
                )
        
        # now correct the room_type_code and try again
        roomType2 = RoomType.objects.create(
                room_type_code='DLX',
                room_type_name='Deluxe Room',
                price=Decimal('110.00'),
                deluxe=True,
                bath=True,
                separate_shower=False,
                maximum_guests=2
            )

        # Confirm room_type was saved, making the count = 2
        self.assertEqual(RoomType.objects.count(), 2)            

class RoomModelTest(TestCase):
    def setUp(self):
        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )
        self.room = Room.objects.create(
            room_number=101,
            room_type=self.room_type
        )

    def test_room_creation(self):
        self.assertEqual(self.room.room_number, 101)
        self.assertEqual(self.room.room_type, self.room_type)

    def test_room_price(self):
        # Test the room price value and type
        self.assertEqual(self.room.room_type.price, Decimal('100.00'))
        self.assertIsInstance(self.room.room_type.price, Decimal)

    def test_room_type_str(self):
        self.assertEqual(str(self.room_type), 'Standard Room')        

    def test_room_str_method(self):
        self.assertEqual(str(self.room), '101')

class ReservationModelTest(TestCase):
    def setUp(self):
        # Create necessary related objects
        self.guest = Guest.objects.create(
            title='Mr',
            first_name='John',
            last_name='Smith',
            phone_number='07123456789',
            email='john.smith@example.com',
            address_line1='123 Main Street',
            city='London',
            county='Greater London',
            postcode='SW1A 1AA'
        )
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
            postcode = 'NR1 1JP')


        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )

        self.room = Room.objects.create(
            room_number=101,
            room_type=self.room_type
        )

        self.reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('200.00'),
            amount_paid=Decimal('100.00'),
            number_of_guests=2,
            start_of_stay=date(2025, 10, 23),
            length_of_stay=3,
            status_code='RE'
        )

    def test_reservation_creation(self):
        self.assertEqual(self.reservation.guest, self.guest)
        self.assertEqual(self.reservation.room_number, self.room)
        self.assertEqual(self.reservation.price, Decimal('200.00'))
        self.assertEqual(self.reservation.status_code, 'RE')

    def test_reservation_str_method(self):
        expected_str = f"Reservation {self.reservation.reservation_id} - RE"
        self.assertEqual(str(self.reservation), expected_str)

    def test_end_date_calculation(self):
        expected_end_date = self.reservation.start_of_stay + timedelta(days=3)
        self.assertEqual(self.reservation.end_date, expected_end_date)

    def test_invalid_guest_count(self):
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                guest=self.guest,
                room_number=self.room,
                reservation_date_time=timezone.now(),
                price=Decimal('200.00'),
                amount_paid=Decimal('100.00'),
                number_of_guests=5,  # More than maximum_guests
                start_of_stay=date(2025, 10, 22),
                length_of_stay=3,
                status_code='RE'
            )
            reservation.clean()

    def test_invalid_payment_amount(self):
        with self.assertRaises(ValidationError):
            reservation = Reservation(
                guest=self.guest,
                room_number=self.room,
                reservation_date_time=timezone.now(),
                price=Decimal('200.00'),
                amount_paid=Decimal('300.00'),  # More than total price
                number_of_guests=2,
                start_of_stay=date(2025, 10, 22),
                length_of_stay=3,
                status_code='RE'
            )
            reservation.clean()

    def test_reservation_double_booking(self):              
        # check that trying to create an overlapping booking is caught with a ValidationError
        # (overlapping the start of self.reservation) 
        with self.assertRaises(ValidationError):
            res2 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room,
                reservation_date_time = timezone.now(),
                price = self.room.room_type.price, # set to the room price at the time of booking
                amount_paid=Decimal('100.00'),
                number_of_guests=2,
                start_of_stay=date(2025, 10, 22),
                length_of_stay=3,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (overlapping the end of self.reservation)
        with self.assertRaises(ValidationError):
            res3 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room,
                reservation_date_time = timezone.now(),
                price = self.room.room_type.price, # set to the room price at the time of booking
                amount_paid=Decimal('100.00'),
                number_of_guests=2,
                start_of_stay=date(2025, 10, 25),
                length_of_stay=1,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (starting before self.reservation and finishing after) 
        with self.assertRaises(ValidationError):
            res4 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room,
                reservation_date_time = timezone.now(),
                price = self.room.room_type.price, # set to the room price at the time of booking
                amount_paid=Decimal('100.00'),
                number_of_guests=2,
                start_of_stay=date(2025, 10, 22),
                length_of_stay=7,
                status_code='RE',  # Reserved
                notes=None
            )

        # check that trying to create an overlapping booking is caught with a ValidationError
        # (start and ends times inside the booking of self.reservation) 
        with self.assertRaises(ValidationError):
            res5 = Reservation.objects.create(
                guest = self.guest2,
                room_number = self.room,
                reservation_date_time = timezone.now(),
                price = self.room.room_type.price, # set to the room price at the time of booking
                amount_paid=Decimal('100.00'),
                number_of_guests=2,
                start_of_stay=date(2025, 10, 24),
                length_of_stay=1,
                status_code='RE',  # Reserved
                notes=None
            )

        # now create two valid bookings, one ending on the same day res1 starts
        res6 = Reservation.objects.create(
            guest = self.guest2,
            room_number = self.room,
            reservation_date_time = timezone.now(),
            price = self.room.room_type.price, # set to the room price at the time of booking
            amount_paid=Decimal('100.00'),
            number_of_guests=2,
            start_of_stay=date(2025, 10, 26),
            length_of_stay=1,
            status_code='RE',  # Reserved
            notes=None
        )            

        # Confirm the reservations were saved, should now have 2
        self.assertEqual(Reservation.objects.count(), 2)
