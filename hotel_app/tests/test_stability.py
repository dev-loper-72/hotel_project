from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta, datetime
import time
import threading
import random
from django.core.exceptions import ValidationError

from hotel_app.models import Guest, RoomType, Room, Reservation

class StabilityTestCase(TestCase):
    """Base class for stability tests with common setup."""
    
    def setUp(self):
        """Set up test data and configurations."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Add necessary permissions
        manager_group = Group.objects.create(name='Manager')
        permissions = Permission.objects.filter(
            codename__in=[
                'add_reservation', 'change_reservation', 'view_reservation', 'delete_reservation',
                'add_guest', 'change_guest', 'view_guest', 'delete_guest',
                'add_room', 'change_room', 'view_room', 'delete_room',
                'add_roomtype', 'change_roomtype', 'view_roomtype', 'delete_roomtype'
            ]
        )
        manager_group.permissions.set(permissions)
        self.user.groups.add(manager_group)
        self.user.save()

        # Create room types
        self.room_types = []
        for i, (code, name, price) in enumerate([
            ('STD', 'Standard Room', '100.00'),
            ('DLX', 'Deluxe Room', '200.00'),
            ('SUT', 'Suite', '300.00'),
            ('FAM', 'Family Room', '250.00')
        ]):
            room_type = RoomType.objects.create(
                room_type_code=code,
                room_type_name=name,
                price=Decimal(price),
                deluxe=i > 0,
                bath=True,
                separate_shower=i > 0,
                maximum_guests=2 + i
            )
            self.room_types.append(room_type)

        # Create rooms
        self.rooms = []
        room_number = 101
        for room_type in self.room_types:
            for _ in range(5):  # 5 rooms per type
                room = Room.objects.create(
                    room_number=room_number,
                    room_type=room_type
                )
                self.rooms.append(room)
                room_number += 1

        self.client.login(username='testuser', password='testpass123')

    def create_test_guest(self, index=1):
        """Helper method to create a test guest."""
        return Guest.objects.create(
            title='Mr',
            first_name=f'Test{index}',
            last_name=f'Guest{index}',
            phone_number=f'0712345{index:04d}',
            email=f'test{index}@example.com',
            address_line1=f'{index} Test Street',
            city='London',
            county='Greater London',
            postcode='SW1A 1AA'
        )

    def create_test_reservation(self, guest, room, start_date, length_of_stay=2):
        """Helper method to create a test reservation."""
        try:
            print(f"Attempting to create reservation for room {room.room_number} starting {start_date}")

            # Check if room is available for these dates
            existing_reservations = Reservation.objects.filter(
                room_number=room,
                start_of_stay__lt=start_date + timedelta(days=length_of_stay),
                status_code__in=['RE', 'IN']
            ).exclude(
                start_of_stay__gte=start_date + timedelta(days=length_of_stay)
            )

            if existing_reservations.exists():
                print(f"Room {room.room_number} already has reservations for {start_date}")
                return None

            # Create reservation with proper validation
            total_price = room.room_type.price * Decimal(str(length_of_stay))
            reservation = Reservation(
                guest=guest,
                room_number=room,
                reservation_date_time=timezone.now(),
                price=total_price,
                amount_paid=total_price,
                number_of_guests=1,
                start_of_stay=start_date,
                length_of_stay=length_of_stay,
                status_code='RE'
            )

            # Validate before saving
            try:
                reservation.full_clean()
                reservation.save()
                print(f"Successfully created reservation for room {room.room_number}")
                return reservation
            except ValidationError as ve:
                print(f"Validation error creating reservation: {str(ve)}")
                return None

        except Exception as e:
            print(f"Exception creating reservation: {str(e)}")
            return None

class LongTermStabilityTest(StabilityTestCase):
    """Test system stability over extended periods with multiple operations."""

    def test_extended_reservation_cycle(self):
        """Test system stability through multiple reservation cycles."""
        # Create multiple guests
        guests = [self.create_test_guest(i) for i in range(1, 6)]
        start_date = date.today() + timedelta(days=30)

        # Track successful reservations
        successful_reservations = 0

        # Create multiple reservations over an extended period
        for i in range(10):  # 10 cycles
            current_date = start_date + timedelta(days=i*7)

            # Each cycle attempts multiple reservations
            for guest in guests:
                # Try different rooms until finding an available one
                for room in self.rooms:
                    reservation = self.create_test_reservation(
                        guest=guest,
                        room=room,
                        start_date=current_date
                    )
                    if reservation:
                        successful_reservations += 1

                        # Simulate reservation lifecycle
                        self.assertEqual(reservation.status_code, 'RE')

                        # Check-in
                        reservation.status_code = 'IN'
                        reservation.save()
                        self.assertEqual(reservation.status_code, 'IN')

                        # Check-out
                        reservation.status_code = 'OT'
                        reservation.save()
                        self.assertEqual(reservation.status_code, 'OT')
                        break  # Found an available room, move to next guest

            # Verify system state after each cycle
            self.assertEqual(Guest.objects.count(), len(guests))
            self.assertEqual(Room.objects.count(), len(self.rooms))
            self.assertGreater(successful_reservations, 0)

class ConcurrentOperationsTest(StabilityTestCase):
    """Test system stability under concurrent operations."""

    def test_concurrent_reservations(self):
        """Test system stability with concurrent reservation operations."""
        from django.db import transaction
        print("\nStarting concurrent reservations test")

        # Create test data
        guests = [self.create_test_guest(i) for i in range(5)]
        print(f"Created {len(guests)} test guests")

        # Select different rooms for each test
        rooms = random.sample(self.rooms, min(5, len(self.rooms)))
        print(f"Selected {len(rooms)} test rooms: {[r.room_number for r in rooms]}")

        start_date = date.today() + timedelta(days=30)
        results = []

        # Create reservations with transaction management
        for i in range(len(rooms)):
            try:
                with transaction.atomic():
                    room = rooms[i]
                    guest = guests[i]
                    unique_date = start_date + timedelta(days=i * 3)

                    print(f"\nAttempt {i}: Starting reservation")
                    print(f"Attempt {i}: Using room {room.room_number} for guest {guest.first_name}")

                    # Check if room is available
                    existing_reservations = Reservation.objects.filter(
                        room_number=room,
                        start_of_stay__lt=unique_date + timedelta(days=2),
                        status_code__in=['RE', 'IN']
                    ).exclude(
                        start_of_stay__gte=unique_date + timedelta(days=2)
                    )

                    if not existing_reservations.exists():
                        reservation = self.create_test_reservation(
                            guest=guest,
                            room=room,
                            start_date=unique_date,
                            length_of_stay=2
                        )
                        if reservation:
                            print(f"Attempt {i}: Successfully created reservation")
                            results.append(reservation)
                        else:
                            print(f"Attempt {i}: Failed to create reservation")
                    else:
                        print(f"Attempt {i}: Room {room.room_number} already booked")

            except Exception as e:
                print(f"Attempt {i}: Exception: {str(e)}")

        # Verify results
        successful_reservations = [r for r in results if isinstance(r, Reservation)]
        print(f"\nTest completed. Successful reservations: {len(successful_reservations)}")
        print(f"Total attempts: {len(results)}")

        self.assertGreater(len(successful_reservations), 0,
                          "No reservations were created successfully")

        # Verify no overlapping reservations
        for i, res1 in enumerate(successful_reservations):
            for res2 in successful_reservations[i+1:]:
                if res1.room_number == res2.room_number:
                    # Same room, check dates don't overlap
                    res1_end = res1.start_of_stay + timedelta(days=res1.length_of_stay)
                    res2_end = res2.start_of_stay + timedelta(days=res2.length_of_stay)

                    self.assertTrue(
                        res1.start_of_stay >= res2_end or res2.start_of_stay >= res1_end,
                        f"Found overlapping reservations for room {res1.room_number} between dates {res1.start_of_stay}-{res1_end} and {res2.start_of_stay}-{res2_end}"
                    )

                    self.assertTrue(
                        res1.start_of_stay >= res2_end or res2.start_of_stay >= res1_end,
                        f"Found overlapping reservations for room {res1.room_number}"
                    )

class ResourceManagementTest(StabilityTestCase):
    """Test system stability with resource management."""

    def test_room_availability_consistency(self):
        """Test consistency of room availability under heavy load."""
        start_date = date.today() + timedelta(days=30)
        guest = self.create_test_guest()

        # Create multiple reservations for different time periods
        for i in range(10):
            current_date = start_date + timedelta(days=i*3)
            room = random.choice(self.rooms)

            # Create reservation
            reservation = self.create_test_reservation(
                guest=guest,
                room=room,
                start_date=current_date
            )

            if reservation:
                # Get all reservations for the current date range
                active_reservations = Reservation.objects.filter(
                    start_of_stay__lte=current_date + timedelta(days=2),
                    status_code__in=['RE', 'IN']
                )

                # Get all rooms that have these reservations
                reserved_room_ids = active_reservations.values_list('room_number', flat=True)

                # Get available rooms (those not in reserved_room_ids)
                available_rooms = Room.objects.exclude(room_number__in=reserved_room_ids)

                # Verify the count is correct
                expected_count = len(self.rooms) - len(set(reserved_room_ids))
                self.assertEqual(available_rooms.count(), expected_count)

    def test_reservation_status_transitions(self):
        """Test stability of reservation status transitions under load."""
        guest = self.create_test_guest()
        start_date = date.today() + timedelta(days=30)

        # Create multiple reservations with different status transitions
        for i in range(10):
            # Try different rooms until we find an available one
            for room in self.rooms:
                reservation = self.create_test_reservation(
                    guest=guest,
                    room=room,
                    start_date=start_date + timedelta(days=i*3)
                )
                if reservation:
                    # Test all valid status transitions
                    valid_transitions = [
                        ('RE', 'IN'),  # Reserved to Checked In
                        ('IN', 'OT'),  # Checked In to Checked Out
                    ]

                    for from_status, to_status in valid_transitions:
                        reservation.status_code = from_status
                        reservation.save()
                        self.assertEqual(reservation.status_code, from_status)

                        reservation.status_code = to_status
                        reservation.save()
                        self.assertEqual(reservation.status_code, to_status)

                    break  # Found an available room, move to next iteration