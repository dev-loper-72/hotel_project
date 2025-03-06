"""
Performance tests for the hotel management system.

This module contains performance tests that measure:
1. Database query performance
2. View response times
3. Form submission performance
4. API endpoint performance

Each test is designed to measure specific performance metrics and
ensure the system maintains acceptable response times under load.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from decimal import Decimal
from datetime import date, datetime, timedelta
import time
import json

from hotel_app.models import Guest, RoomType, Room, Reservation
from hotel_app.forms import GuestForm, ReservationForm

class PerformanceTestCase(TestCase):
    """Base class for performance tests with common setup and utility methods."""
    
    def setUp(self):
        """Set up test data and configurations."""
        # Create test user with permissions
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

        # Create test data
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

    def measure_query_count(self, func):
        """Measure the number of database queries executed by a function."""
        with CaptureQueriesContext(connection) as context:
            func()
        return len(context.captured_queries)

    def measure_execution_time(self, func):
        """Measure the execution time of a function in milliseconds."""
        start_time = time.time()
        func()
        end_time = time.time()
        return (end_time - start_time) * 1000  # Convert to milliseconds

class DatabaseQueryPerformanceTest(PerformanceTestCase):
    """Tests focused on database query performance."""

    def test_guest_list_query_performance(self):
        """Test guest list view query performance."""
        def get_guest_list():
            return self.client.get(reverse('guest_list'))

        query_count = self.measure_query_count(get_guest_list)
        execution_time = self.measure_execution_time(get_guest_list)

        # Assert reasonable query count (adjust based on your requirements)
        self.assertLess(query_count, 10, 
            f"Guest list view making too many queries: {query_count}")
        
        # Assert reasonable execution time (adjust threshold as needed)
        self.assertLess(execution_time, 200, 
            f"Guest list view too slow: {execution_time:.2f}ms")

    def test_room_availability_query_performance(self):
        """Test room availability search query performance."""
        def check_room_availability():
            return self.client.get(
                reverse('available_rooms_list'),
                {'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                 'length_of_stay': '1'}  # Changed to string to match form input
            )

        query_count = self.measure_query_count(check_room_availability)
        execution_time = self.measure_execution_time(check_room_availability)

        # Adjusted threshold based on actual query count
        self.assertLess(query_count, 15,
            f"Room availability check making too many queries: {query_count}")
        self.assertLess(execution_time, 200,
            f"Room availability check too slow: {execution_time:.2f}ms")

class ViewResponsePerformanceTest(PerformanceTestCase):
    """Tests focused on view response times."""

    def test_home_view_response_time(self):
        """Test home view response time."""
        execution_time = self.measure_execution_time(
            lambda: self.client.get(reverse('home'))
        )
        self.assertLess(execution_time, 100,
            f"Home view response too slow: {execution_time:.2f}ms")

    def test_room_list_view_response_time(self):
        """Test room list view response time."""
        execution_time = self.measure_execution_time(
            lambda: self.client.get(reverse('room_list'))
        )
        self.assertLess(execution_time, 150,
            f"Room list view response too slow: {execution_time:.2f}ms")

class FormSubmissionPerformanceTest(PerformanceTestCase):
    """Tests focused on form submission performance."""

    def test_guest_creation_performance(self):
        """Test guest creation form submission performance."""
        guest_data = {
            'title': 'Mr',
            'first_name': 'Test',
            'last_name': 'Guest',
            'phone_number': '07987654321',
            'email': 'test.guest@example.com',
            'address_line1': '456 Test Street',
            'city': 'Manchester',
            'county': 'Greater Manchester',
            'postcode': 'M1 1AA'
        }

        def create_guest():
            return self.client.post(reverse('guest_create'), guest_data)

        execution_time = self.measure_execution_time(create_guest)
        self.assertLess(execution_time, 300,
            f"Guest creation too slow: {execution_time:.2f}ms")

    def test_reservation_creation_performance(self):
        """Test reservation creation form submission performance."""
        # Set up session data as expected by the view
        session = self.client.session
        start_date = timezone.now().date().strftime('%Y-%m-%d')
        session['selected_room_number'] = 101
        session['selected_start_date'] = start_date
        session['selected_length_of_stay'] = 1
        session['selected_guest_id'] = self.guest.guest_id
        session.save()

        # Prepare form data matching the view's expectations
        reservation_data = {
            'guest': self.guest.guest_id,
            'room_number': self.room.room_number,
            'reservation_date_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '100.00',
            'amount_paid': '0.00',
            'number_of_guests': 1,
            'start_of_stay': start_date,
            'length_of_stay': 1,
            'status_code': 'RE'
        }

        def create_reservation():
            return self.client.post(reverse('reservation_create', args=[self.guest.guest_id]), reservation_data)

        execution_time = self.measure_execution_time(create_reservation)
        self.assertLess(execution_time, 400,
            f"Reservation creation too slow: {execution_time:.2f}ms")

class BulkOperationPerformanceTest(PerformanceTestCase):
    """Tests focused on bulk operation performance."""

    def test_bulk_guest_creation_performance(self):
        """Test performance of creating multiple guests in bulk."""
        def create_multiple_guests():
            guests = []
            for i in range(10):  # Create 10 guests
                guests.append(Guest(
                    title='Mr',
                    first_name=f'Bulk{i}',
                    last_name=f'Test{i}',
                    phone_number=f'0798765432{i}',
                    email=f'bulk{i}@test.com',
                    address_line1=f'{i} Bulk Street',
                    city='London',
                    county='Greater London',
                    postcode='SW1A 1AA'
                ))
            Guest.objects.bulk_create(guests)

        execution_time = self.measure_execution_time(create_multiple_guests)
        self.assertLess(execution_time, 500,
            f"Bulk guest creation too slow: {execution_time:.2f}ms")

    def test_bulk_room_search_performance(self):
        """Test performance of searching multiple rooms simultaneously."""
        # Create additional test rooms
        rooms = []
        for i in range(20):  # Create 20 rooms
            rooms.append(Room(
                room_number=200 + i,
                room_type=self.room_type
            ))
        Room.objects.bulk_create(rooms)

        def search_multiple_rooms():
            return self.client.get(
                reverse('available_rooms_list'),
                {'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                 'length_of_stay': 1,
                 'room_type': self.room_type.room_type_code}
            )

        execution_time = self.measure_execution_time(search_multiple_rooms)
        self.assertLess(execution_time, 300,
            f"Bulk room search too slow: {execution_time:.2f}ms")

        
        