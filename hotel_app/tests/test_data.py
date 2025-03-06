from django.test import TestCase
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone
from hotel_app.models import Guest, RoomType, Room, Reservation
from django.core.exceptions import ValidationError
from django.db import models

class TestDataGenerator(TestCase):
    """Test class for generating and testing a comprehensive set of hotel data."""

    def setUp(self):
        """Create a full set of test data including room types, rooms, and guests."""
        self.create_room_types()
        self.create_rooms()
        self.create_guests()
        self.create_reservations()

    def create_room_types(self):
        """Create a variety of room types with different characteristics."""
        self.room_types = [
            RoomType.objects.create(
                room_type_code='STD',
                room_type_name='Standard Room',
                price=Decimal('100.00'),
                deluxe=False,
                bath=True,
                separate_shower=False,
                maximum_guests=2
            ),
            RoomType.objects.create(
                room_type_code='DLX',
                room_type_name='Deluxe Room',
                price=Decimal('150.00'),
                deluxe=True,
                bath=True,
                separate_shower=True,
                maximum_guests=2
            ),
            RoomType.objects.create(
                room_type_code='FAM',
                room_type_name='Family Room',
                price=Decimal('200.00'),
                deluxe=False,
                bath=True,
                separate_shower=True,
                maximum_guests=4
            ),
            RoomType.objects.create(
                room_type_code='STE',
                room_type_name='Suite',
                price=Decimal('300.00'),
                deluxe=True,
                bath=True,
                separate_shower=True,
                maximum_guests=3
            ),
            RoomType.objects.create(
                room_type_code='PEN',
                room_type_name='Penthouse Suite',
                price=Decimal('500.00'),
                deluxe=True,
                bath=True,
                separate_shower=True,
                maximum_guests=4
            ),
            RoomType.objects.create(
                room_type_code='ECO',
                room_type_name='Economy Room',
                price=Decimal('75.00'),
                deluxe=False,
                bath=False,
                separate_shower=True,
                maximum_guests=2
            ),
            RoomType.objects.create(
                room_type_code='TWN',
                room_type_name='Twin Room',
                price=Decimal('120.00'),
                deluxe=False,
                bath=True,
                separate_shower=False,
                maximum_guests=2
            ),
            RoomType.objects.create(
                room_type_code='ACC',
                room_type_name='Accessible Room',
                price=Decimal('100.00'),
                deluxe=False,
                bath=False,
                separate_shower=True,
                maximum_guests=2
            )
        ]

    def create_rooms(self):
        """Create rooms of different types across different floors."""
        self.rooms = []
        
        # Ground floor - Accessible rooms (101-103)
        for i in range(1, 4):
            self.rooms.append(Room.objects.create(
                room_number=100 + i,
                room_type=RoomType.objects.get(room_type_code='ACC')
            ))

        # First floor - Standard and Economy rooms (111-115)
        for i in range(1, 4):
            self.rooms.append(Room.objects.create(
                room_number=110 + i,
                room_type=RoomType.objects.get(room_type_code='STD')
            ))
        for i in range(4, 6):
            self.rooms.append(Room.objects.create(
                room_number=110 + i,
                room_type=RoomType.objects.get(room_type_code='ECO')
            ))

        # Second floor - Deluxe and Twin rooms (121-125)
        for i in range(1, 4):
            self.rooms.append(Room.objects.create(
                room_number=120 + i,
                room_type=RoomType.objects.get(room_type_code='DLX')
            ))
        for i in range(4, 6):
            self.rooms.append(Room.objects.create(
                room_number=120 + i,
                room_type=RoomType.objects.get(room_type_code='TWN')
            ))

        # Third floor - Family rooms and Suites (131-134)
        for i in range(1, 3):
            self.rooms.append(Room.objects.create(
                room_number=130 + i,
                room_type=RoomType.objects.get(room_type_code='FAM')
            ))
        for i in range(3, 5):
            self.rooms.append(Room.objects.create(
                room_number=130 + i,
                room_type=RoomType.objects.get(room_type_code='STE')
            ))

        # Top floor - Penthouse (141-142)
        for i in range(1, 3):
            self.rooms.append(Room.objects.create(
                room_number=140 + i,
                room_type=RoomType.objects.get(room_type_code='PEN')
            ))

    def create_guests(self):
        """Create a diverse set of test guests."""
        self.guests = [
            Guest.objects.create(
                title='Mr',
                first_name='James',
                last_name='Smith',
                phone_number='07123456789',
                email='james.smith@example.com',
                address_line1='123 High Street',
                city='London',
                county='Greater London',
                postcode='SW1A 1AA'
            ),
            Guest.objects.create(
                title='Mrs',
                first_name='Sarah',
                last_name='Johnson',
                phone_number='07234567890',
                email='sarah.j@example.com',
                address_line1='45 Church Lane',
                city='Manchester',
                county='Greater Manchester',
                postcode='M1 1AA'
            ),
            Guest.objects.create(
                title='Dr',
                first_name='Michael',
                last_name='Williams',
                phone_number='07345678901',
                email='dr.williams@example.com',
                address_line1='789 Science Park',
                city='Cambridge',
                county='Cambridgeshire',
                postcode='CB2 1TN'
            ),
            Guest.objects.create(
                title='Ms',
                first_name='Emma',
                last_name='Brown',
                phone_number='07456789012',
                email='emma.b@example.com',
                address_line1='12 Queen Street',
                city='Edinburgh',
                county='Midlothian',
                postcode='EH1 1YZ'
            ),
            Guest.objects.create(
                title='Prof',
                first_name='David',
                last_name='Taylor',
                phone_number='07567890123',
                email='d.taylor@example.com',
                address_line1='56 University Road',
                city='Oxford',
                county='Oxfordshire',
                postcode='OX1 2JD'
            ),
            Guest.objects.create(
                title='Mrs',
                first_name='Lisa',
                last_name='Anderson',
                phone_number='07678901234',
                email='l.anderson@example.com',
                address_line1='34 Park Avenue',
                city='Bristol',
                county='Bristol',
                postcode='BS1 4ND'
            ),
            Guest.objects.create(
                title='Mr',
                first_name='Robert',
                last_name='Wilson',
                phone_number='07789012345',
                email='r.wilson@example.com',
                address_line1='67 Marina Way',
                city='Brighton',
                county='East Sussex',
                postcode='BN1 3WA'
            ),
            Guest.objects.create(
                title='Dr',
                first_name='Helen',
                last_name='Davies',
                phone_number='07890123456',
                email='h.davies@example.com',
                address_line1='89 Hospital Close',
                city='Leeds',
                county='West Yorkshire',
                postcode='LS1 3EX'
            ),
            Guest.objects.create(
                title='Sir',
                first_name='Richard',
                last_name='Hughes',
                phone_number='07901234567',
                email='sir.hughes@example.com',
                address_line1='123 Manor House',
                city='Bath',
                county='Somerset',
                postcode='BA1 2QT'
            ),
            Guest.objects.create(
                title='Dame',
                first_name='Victoria',
                last_name='Pembroke',
                phone_number='07012345678',
                email='v.pembroke@example.com',
                address_line1='45 Royal Crescent',
                city='York',
                county='North Yorkshire',
                postcode='YO1 7HG'
            )
        ]

    def create_reservations(self):
        """Create a set of test reservations with various scenarios."""
        today = date.today()
        
        # Current active reservation
        Reservation.objects.create(
            guest=self.guests[0],
            room_number=Room.objects.get(room_number=101),
            reservation_date_time=timezone.make_aware(datetime.now() - timedelta(days=7)),
            price=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            number_of_guests=2,
            start_of_stay=today - timedelta(days=1),
            length_of_stay=3,
            status_code='IN'
        )

        # Future reservations
        Reservation.objects.create(
            guest=self.guests[1],
            room_number=Room.objects.get(room_number=131),
            reservation_date_time=timezone.make_aware(datetime.now() - timedelta(days=14)),
            price=Decimal('600.00'),
            amount_paid=Decimal('200.00'),
            number_of_guests=3,
            start_of_stay=today + timedelta(days=7),
            length_of_stay=3,
            status_code='RE'
        )

        # Past completed reservation
        Reservation.objects.create(
            guest=self.guests[2],
            room_number=Room.objects.get(room_number=141),
            reservation_date_time=timezone.make_aware(datetime.now() - timedelta(days=30)),
            price=Decimal('1500.00'),
            amount_paid=Decimal('1500.00'),
            number_of_guests=2,
            start_of_stay=today - timedelta(days=15),
            length_of_stay=3,
            status_code='OT'
        )

    def test_room_type_creation(self):
        """Test that all room types were created correctly."""
        self.assertEqual(RoomType.objects.count(), 8)
        self.assertTrue(RoomType.objects.filter(room_type_code='PEN').exists())
        penthouse = RoomType.objects.get(room_type_code='PEN')
        self.assertEqual(penthouse.price, Decimal('500.00'))
        self.assertTrue(penthouse.deluxe)

    def test_room_creation(self):
        """Test that all rooms were created correctly."""
        # Count rooms by type
        acc_rooms = Room.objects.filter(room_type__room_type_code='ACC').count()
        std_eco_rooms = Room.objects.filter(room_type__room_type_code__in=['STD', 'ECO']).count()
        dlx_twn_rooms = Room.objects.filter(room_type__room_type_code__in=['DLX', 'TWN']).count()
        fam_ste_rooms = Room.objects.filter(room_type__room_type_code__in=['FAM', 'STE']).count()
        pen_rooms = Room.objects.filter(room_type__room_type_code='PEN').count()

        # Verify counts by floor
        self.assertEqual(acc_rooms, 3, "Should be 3 accessible rooms")
        self.assertEqual(std_eco_rooms, 5, "Should be 5 standard/economy rooms")
        self.assertEqual(dlx_twn_rooms, 5, "Should be 5 deluxe/twin rooms")
        self.assertEqual(fam_ste_rooms, 4, "Should be 4 family/suite rooms")
        self.assertEqual(pen_rooms, 2, "Should be 2 penthouse rooms")

        # Verify total count
        total_rooms = Room.objects.count()
        self.assertEqual(total_rooms, 19, "Total should be 19 rooms")

    def test_guest_creation(self):
        """Test that all guests were created correctly."""
        self.assertEqual(Guest.objects.count(), 10)
        # Test specific guest details
        prof = Guest.objects.get(title='Prof')
        self.assertEqual(prof.first_name, 'David')
        self.assertEqual(prof.last_name, 'Taylor')

    def test_reservation_creation(self):
        """Test that reservations were created correctly."""
        self.assertEqual(Reservation.objects.count(), 3)
        # Test reservation statuses
        self.assertEqual(Reservation.objects.filter(status_code='IN').count(), 1)
        self.assertEqual(Reservation.objects.filter(status_code='RE').count(), 1)
        self.assertEqual(Reservation.objects.filter(status_code='OT').count(), 1)

    def test_room_availability(self):
        """Test room availability checking."""
        today = date.today()
        future_date = today + timedelta(days=7)  # Looking for availability a week from now

        # Should find available penthouse
        available_penthouses = Room.objects.filter(
            room_type__room_type_code='PEN'
        ).exclude(  # Exclude rooms with overlapping reservations
            reservations__status_code__in=['RE', 'IN'],
            reservations__start_of_stay__lte=future_date,
            reservations__start_of_stay__gte=future_date - timedelta(days=365)  # Limit search to reasonable range
        ).exclude(  # Also exclude if the stay extends into our desired date
            reservations__status_code__in=['RE', 'IN'],
            reservations__start_of_stay__lte=future_date,
            reservations__start_of_stay__gt=future_date - timedelta(days=30)  # Look back 30 days
        ).distinct()  # Ensure we don't get duplicates

        self.assertTrue(available_penthouses.exists(), "Should find at least one available penthouse")
        self.assertGreaterEqual(available_penthouses.count(), 1)

    def test_guest_validation(self):
        """Test guest data validation."""
        invalid_guest = Guest(
            title='Invalid',  # Invalid title
            first_name='Test',
            last_name='User',
            phone_number='07123456789',
            email='test@example.com',
            address_line1='123 Test St',
            city='London',
            county='Greater London',
            postcode='SW1A 1AA'
        )
        with self.assertRaises(ValidationError):
            invalid_guest.full_clean()

    def test_reservation_validation(self):
        """Test reservation validation rules."""
        # Test guest count validation
        today = date.today()
        invalid_reservation = Reservation(
            guest=self.guests[3],
            room_number=Room.objects.get(room_number=101),  # Accessible room with max 2 guests
            reservation_date_time=timezone.make_aware(datetime.now()),
            price=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            number_of_guests=5,  # Exceeds room capacity
            start_of_stay=today,
            length_of_stay=3,
            status_code='RE'
        )
        with self.assertRaises(ValidationError):
            invalid_reservation.full_clean()