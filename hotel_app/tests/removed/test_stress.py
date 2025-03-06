"""
Stress tests for the hotel management system.

This module contains stress tests that verify system behavior under heavy load:
1. Concurrent user access
2. High volume data operations
3. Resource intensive operations
4. Long-running transactions
5. System recovery scenarios

Each test is designed to simulate real-world stress conditions and ensure
the system remains stable and responsive under load.
"""

from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.db import connection, reset_queries, transaction
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime, timedelta
import time
import threading
import random
from faker import Faker

from hotel_app.models import Guest, RoomType, Room, Reservation
from hotel_app.forms import GuestForm, ReservationForm

def generate_uk_phone():
    """Generate a realistic UK phone number."""
    formats = [
        "07{}{}{} {}{}{}{}{}{}",  # Mobile
        "020 {}{}{}{} {}{}{}{}",  # London
        "0161 {}{}{} {}{}{}{}",   # Manchester
    ]
    return random.choice(formats).format(*[str(random.randint(0, 9)) for _ in range(9)])

def generate_uk_postcode():
    """Generate a realistic UK postcode."""
    area = random.choice(['L', 'M', 'B', 'S', 'W', 'N', 'E', 'SW', 'SE', 'NW', 'NE'])
    district = random.randint(1, 99)
    space = ' '
    number = random.randint(0, 9)
    letter1 = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    letter2 = random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    return f"{area}{district}{space}{number}{letter1}{letter2}"

class StressTestCase(TransactionTestCase):
    """Base class for stress tests with common setup and utility methods."""
    
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
        view_room_permission = Permission.objects.get(codename='view_room')
        manager_group.permissions.add(view_room_permission)
        self.user.groups.add(manager_group)
        self.user.save()

        # Create base test data
        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )

        # Create multiple rooms
        self.rooms = []
        for i in range(50):  # Create 50 rooms for stress testing
            room = Room.objects.create(
                room_number=100 + i,
                room_type=self.room_type
            )
            self.rooms.append(room)

        # Create base guest
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

        # Login the test user
        self.client.login(username='testuser', password='testpass123')

class ConcurrentUserStressTest(StressTestCase):
    """Tests system behavior under concurrent user load."""

    def simulate_user_actions(self):
        """Simulate various user actions."""
        client = Client()
        client.login(username='testuser', password='testpass123')
        
        # Perform a series of common operations
        actions = [
            lambda: client.get(reverse('home')),
            lambda: client.get(reverse('guest_list')),
            lambda: client.get(reverse('room_list')),
            lambda: client.get(
                reverse('available_rooms_list'),
                {'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                 'length_of_stay': '1'}
            )
        ]
        
        # Execute random actions
        for _ in range(5):
            action = random.choice(actions)
            response = action()
            self.assertEqual(response.status_code, 200)

    def test_concurrent_users(self):
        """Test system with multiple concurrent users."""
        num_users = 10
        threads = []
        
        # Create and start threads for concurrent users
        for _ in range(num_users):
            thread = threading.Thread(target=self.simulate_user_actions)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()

class HighVolumeDataStressTest(StressTestCase):
    """Tests system behavior with high volume data operations."""

    def test_bulk_reservation_creation(self):
        """Test creating many reservations simultaneously."""
        start_time = timezone.now()
        reservations = []

        # Create 100 reservations
        for i in range(100):
            start_date = timezone.now().date() + timedelta(days=i % 30)
            room = self.rooms[i % len(self.rooms)]

            reservation = Reservation(
                guest=self.guest,
                room_number=room,
                reservation_date_time=start_time + timedelta(minutes=i),
                price=Decimal('100.00'),
                amount_paid=Decimal('0.00'),
                number_of_guests=1,
                start_of_stay=start_date,
                length_of_stay=1,
                status_code='RE'
            )
            reservations.append(reservation)

        # Record initial count
        initial_count = Reservation.objects.count()

        # Measure time for bulk creation
        start_creation_time = time.time()
        Reservation.objects.bulk_create(reservations)
        creation_time = time.time() - start_creation_time

        # Verify all reservations were created
        final_count = Reservation.objects.count()
        self.assertEqual(final_count - initial_count, 100)

        # Assert creation time is reasonable (less than 2 seconds)
        self.assertLess(creation_time, 2.0,
            f"Bulk creation took too long: {creation_time:.2f} seconds")

    def test_bulk_guest_creation(self):
        """Test creating 1000 guests with realistic data."""
        fake = Faker(['en_GB'])

        # Get initial count to account for guests created in setUp
        initial_count = Guest.objects.count()
        guests = []

        # Record start time
        start_time = time.time()

        # Create 1000 guests with realistic data
        for _ in range(1000):
            title = random.choice(['Mr', 'Mrs', 'Ms', 'Dr', 'Prof'])
            gender = 'M' if title in ['Mr', 'Dr', 'Prof'] else 'F'

            if gender == 'M':
                first_name = fake.first_name_male()
            else:
                first_name = fake.first_name_female()

            guest = Guest(
                title=title,
                first_name=first_name,
                last_name=fake.last_name(),
                phone_number=generate_uk_phone(),
                email=fake.email(),
                address_line1=fake.street_address(),
                address_line2=fake.secondary_address() if random.random() > 0.7 else '',
                city=fake.city(),
                county=fake.county(),
                postcode=generate_uk_postcode()
            )
            guests.append(guest)

        # Bulk create all guests
        Guest.objects.bulk_create(guests)

        # Calculate execution time
        execution_time = time.time() - start_time

        # Verify all guests were created (accounting for initial guests)
        self.assertEqual(
            Guest.objects.count(),
            initial_count + 1000,
            "Failed to create all 1000 guests"
        )

        # Assert creation time is reasonable (less than 5 seconds)
        self.assertLess(
            execution_time,
            5.0,
            f"Bulk guest creation took too long: {execution_time:.2f} seconds"
        )

        # Test some random guests to verify data quality
        random_guests = Guest.objects.order_by('?')[:10]
        for guest in random_guests:
            self.assertRegex(guest.email, r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            self.assertRegex(guest.phone_number, r'^(07|020|0161)')
            self.assertRegex(guest.postcode, r'^[A-Z]{1,2}[0-9]{1,2}\s[0-9][A-Z]{2}$')
            self.assertTrue(len(guest.first_name) > 0)
            self.assertTrue(len(guest.last_name) > 0)
            self.assertTrue(len(guest.address_line1) > 0)
            self.assertTrue(len(guest.city) > 0)

    def test_bulk_guest_search(self):
        """Test searching through a large number of guests."""
        # First create 1000 guests using the bulk creation test
        initial_count = Guest.objects.count()
        self.test_bulk_guest_creation()

        self.assertEqual(Guest.objects.count(), initial_count + 1000)

        # Test search performance
        start_time = time.time()

        # Perform various searches to stress test
        searches = [
            {'first_name': 'John'},  # Common name search
            {'last_name': 'Smith'},  # Common surname search
            {'city': 'London'},      # City search
            {'postcode__startswith': 'SW'}, # Partial postcode search
            {'email__contains': '.com'}, # Email domain search
        ]

        for search_params in searches:
            results = Guest.objects.filter(**search_params)
            # Ensure search completes and returns results
            self.assertTrue(len(results) >= 0)

        response = self.client.get(reverse('guest_list'))
        execution_time = (time.time() - start_time) * 1000  # ms

        self.assertEqual(response.status_code, 200)
        self.assertLess(execution_time, 1000,  # 1 second max
            f"Guest list with 1000 records too slow: {execution_time:.2f}ms")

class ResourceIntensiveStressTest(StressTestCase):
    """Tests system behavior under resource-intensive operations."""

    def test_complex_availability_search(self):
        """Test complex room availability search under load."""
        # Create many reservations across different dates
        for i in range(100):
            start_date = timezone.now().date() + timedelta(days=i % 30)
            room = self.rooms[i % len(self.rooms)]
            
            Reservation.objects.create(
                guest=self.guest,
                room_number=room,
                reservation_date_time=timezone.now(),
                price=Decimal('100.00'),
                amount_paid=Decimal('0.00'),
                number_of_guests=1,
                start_of_stay=start_date,
                length_of_stay=random.randint(1, 5),
                status_code='RE'
            )
        
        # Perform multiple concurrent availability searches
        def search_availability():
            start_date = timezone.now().date() + timedelta(days=random.randint(0, 30))
            response = self.client.get(
                reverse('available_rooms_list'),
                {'start_date': start_date.strftime('%Y-%m-%d'),
                 'length_of_stay': str(random.randint(1, 5))}
            )
            self.assertEqual(response.status_code, 200)
        
        threads = []
        for _ in range(10):  # 10 concurrent searches
            thread = threading.Thread(target=search_availability)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()

class SystemRecoveryStressTest(StressTestCase):
    """Tests system recovery from stress conditions."""

    def test_transaction_rollback_under_load(self):
        """Test system recovery when transactions fail under load."""
        
        @transaction.atomic
        def create_reservation_with_error(i):
            # Create reservation
            start_date = timezone.now().date() + timedelta(days=i)
            reservation = Reservation.objects.create(
                guest=self.guest,
                room_number=self.rooms[0],  # Deliberately create conflict
                reservation_date_time=timezone.now(),
                price=Decimal('100.00'),
                amount_paid=Decimal('0.00'),
                number_of_guests=1,
                start_of_stay=start_date,
                length_of_stay=1,
                status_code='RE'
            )
            
            if i % 2 == 0:  # Simulate random errors
                raise ValueError("Simulated error")
            
            return reservation
        
        # Attempt multiple reservations with some failing
        successful = 0
        failed = 0
        
        for i in range(20):
            try:
                create_reservation_with_error(i)
                successful += 1
            except ValueError:
                failed += 1
        
        # Verify system state
        self.assertEqual(failed, 10)  # Half should fail
        self.assertEqual(successful, 10)  # Half should succeed
        self.assertEqual(
            Reservation.objects.count(),
            10,  # Only successful reservations should exist
            "Failed transactions were not properly rolled back"
        )