"""
Load tests for the hotel management system.

This module contains load tests that simulate sustained real-world usage:
1. Sustained concurrent user sessions
2. Mixed workload patterns
3. Peak hour simulation
4. Background task impact
5. Cache effectiveness

Each test is designed to simulate realistic usage patterns and ensure
the system maintains performance under sustained load.
"""

from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.db import connection, reset_queries, transaction
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
import time
import threading
import random
from faker import Faker
import statistics

from hotel_app.models import Guest, RoomType, Room, Reservation
from hotel_app.forms import GuestForm, ReservationForm

class LoadTestCase(TransactionTestCase):
    """Base class for load tests with common setup and utility methods."""
    
    def setUp(self):
        """Set up test data and configurations."""
        self.client = Client()
        self.fake = Faker(['en_GB'])
        
        # Create test users with different roles
        self.create_test_users()
        
        # Create room types
        self.create_room_types()
        
        # Create rooms
        self.create_rooms()
        
        # Create initial guests
        self.create_initial_guests()
        
        # Create initial reservations
        self.create_initial_reservations()

    def create_test_users(self):
        """Create users with different roles."""
        # Create manager user
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123'
        )
        manager_group = Group.objects.create(name='Manager')
        self.manager.groups.add(manager_group)
        
        # Create staff users
        self.staff_users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'staff{i}',
                email=f'staff{i}@example.com',
                password='staffpass123'
            )
            self.staff_users.append(user)

    def create_room_types(self):
        """Create different room types."""
        self.room_types = []
        types = [
            ('STD', 'Standard Room', 100, False, True, False, 2),
            ('DLX', 'Deluxe Room', 200, True, True, True, 2),
            ('SUT', 'Suite', 300, True, True, True, 4),
            ('FAM', 'Family Room', 250, False, True, True, 6)
        ]
        
        for code, name, price, deluxe, bath, shower, max_guests in types:
            room_type = RoomType.objects.create(
                room_type_code=code,
                room_type_name=name,
                price=Decimal(str(price)),
                deluxe=deluxe,
                bath=bath,
                separate_shower=shower,
                maximum_guests=max_guests
            )
            self.room_types.append(room_type)

    def create_rooms(self):
        """Create rooms of different types."""
        self.rooms = []
        floor_start = 1
        
        for room_type in self.room_types:
            # Create 25 rooms of each type
            for i in range(25):
                room_number = (floor_start * 100) + i + 1
                room = Room.objects.create(
                    room_number=room_number,
                    room_type=room_type
                )
                self.rooms.append(room)
            floor_start += 1

    def create_initial_guests(self):
        """Create initial set of guests."""
        self.guests = []
        for _ in range(50):
            guest = Guest.objects.create(
                title=random.choice(['Mr', 'Mrs', 'Ms', 'Dr']),
                first_name=self.fake.first_name(),
                last_name=self.fake.last_name(),
                phone_number=self.fake.phone_number(),
                email=self.fake.email(),
                address_line1=self.fake.street_address(),
                city=self.fake.city(),
                county=self.fake.county(),
                postcode=self.fake.postcode()
            )
            self.guests.append(guest)

    def create_initial_reservations(self):
        """Create initial set of reservations with non-overlapping dates."""
        self.reservations = []
        base_start_date = timezone.now().date()

        # Create a dictionary to track the last end date for each room
        room_last_dates = {room: base_start_date for room in self.rooms}

        for _ in range(30):
            # Try to create a valid reservation
            attempts = 0
            while attempts < 10:  # Limit attempts to prevent infinite loops
                guest = random.choice(self.guests)
                room = random.choice(self.rooms)
                length_of_stay = random.randint(1, 7)

                # Get the earliest possible start date for this room
                start_date = room_last_dates[room]

                try:
                    reservation = Reservation.objects.create(
                        guest=guest,
                        room_number=room,
                        reservation_date_time=timezone.now(),
                        price=room.room_type.price * length_of_stay,
                        amount_paid=Decimal('0.00'),
                        number_of_guests=random.randint(1, room.room_type.maximum_guests),
                        start_of_stay=start_date,
                        length_of_stay=length_of_stay,
                        status_code='RE'
                    )
                    # Update the last end date for this room
                    room_last_dates[room] = start_date + timedelta(days=length_of_stay + 1)  # Add 1 day buffer
                    self.reservations.append(reservation)
                    break
                except ValidationError:
                    attempts += 1
                    # If validation fails, try with a different room or later date
                    room_last_dates[room] += timedelta(days=1)
                    continue

    def simulate_user_session(self, username, duration=60):
        """Simulate a user session with realistic timing and actions."""
        client = Client()
        client.login(username=username, password='staffpass123')
        
        start_time = time.time()
        response_times = []
        
        while time.time() - start_time < duration:
            # Simulate user thinking time
            time.sleep(random.uniform(1, 3))
            
            # Random action selection with weighted probabilities
            action = random.choices(
                ['view_home', 'list_guests', 'search_rooms', 'view_reservation', 'create_guest'],
                weights=[0.1, 0.3, 0.4, 0.15, 0.05],
                k=1
            )[0]
            
            action_start = time.time()
            
            try:
                if action == 'view_home':
                    response = client.get(reverse('home'))
                elif action == 'list_guests':
                    response = client.get(reverse('guest_list'))
                elif action == 'search_rooms':
                    search_date = timezone.now().date() + timedelta(days=random.randint(0, 30))
                    response = client.get(
                        reverse('available_rooms_list'),
                        {'start_date': search_date.strftime('%Y-%m-%d'),
                         'length_of_stay': str(random.randint(1, 5))}
                    )
                elif action == 'view_reservation':
                    if self.reservations:
                        reservation = random.choice(self.reservations)
                        response = client.get(
                            reverse('reservation_detail', args=[reservation.reservation_id])
                        )
                elif action == 'create_guest':
                    guest_data = {
                        'title': random.choice(['Mr', 'Mrs', 'Ms', 'Dr']),
                        'first_name': self.fake.first_name(),
                        'last_name': self.fake.last_name(),
                        'phone_number': self.fake.phone_number(),
                        'email': self.fake.email(),
                        'address_line1': self.fake.street_address(),
                        'city': self.fake.city(),
                        'county': self.fake.county(),
                        'postcode': self.fake.postcode()
                    }
                    response = client.post(reverse('guest_create'), guest_data)
                
                response_time = (time.time() - action_start) * 1000  # Convert to milliseconds
                response_times.append(response_time)
                
                self.assertEqual(response.status_code, 200)
                
            except Exception as e:
                print(f"Error in user session {username}: {str(e)}")
        
        return response_times

class SustainedLoadTest(LoadTestCase):
    """Tests system behavior under sustained load."""

    def test_sustained_concurrent_users(self):
        """Test system with sustained concurrent user sessions."""
        num_users = 10
        session_duration = 120  # 2 minutes
        all_response_times = []
        
        def run_user_session(username):
            response_times = self.simulate_user_session(f'staff{username}', session_duration)
            all_response_times.extend(response_times)
        
        # Start concurrent user sessions
        threads = []
        for i in range(num_users):
            thread = threading.Thread(target=run_user_session, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all sessions to complete
        for thread in threads:
            thread.join()
        
        # Analyze response times
        avg_response_time = statistics.mean(all_response_times)
        percentile_95 = statistics.quantiles(all_response_times, n=20)[-1]
        
        # Assert performance metrics
        self.assertLess(avg_response_time, 500,
            f"Average response time too high: {avg_response_time:.2f}ms")
        self.assertLess(percentile_95, 1000,
            f"95th percentile response time too high: {percentile_95:.2f}ms")

class PeakLoadTest(LoadTestCase):
    """Tests system behavior during simulated peak hours."""

    def test_peak_hour_performance(self):
        """Test system performance during simulated peak hours."""
        peak_users = 20
        peak_duration = 300  # 5 minutes
        all_response_times = []
        
        # Create additional test data to simulate peak load
        self.create_initial_guests()  # Add more guests
        self.create_initial_reservations()  # Add more reservations
        
        def run_peak_session(username):
            response_times = self.simulate_user_session(f'staff{username}', peak_duration)
            all_response_times.extend(response_times)
        
        # Start peak load simulation
        threads = []
        for i in range(peak_users):
            thread = threading.Thread(target=run_peak_session, args=(i,))
            threads.append(thread)
            # Stagger thread starts to simulate gradual load increase
            time.sleep(random.uniform(0, 2))
            thread.start()
        
        # Wait for all sessions to complete
        for thread in threads:
            thread.join()
        
        # Analyze performance metrics
        avg_response_time = statistics.mean(all_response_times)
        percentile_95 = statistics.quantiles(all_response_times, n=20)[-1]
        max_response_time = max(all_response_times)
        
        # Assert performance metrics
        self.assertLess(avg_response_time, 750,
            f"Average response time during peak load too high: {avg_response_time:.2f}ms")
        self.assertLess(percentile_95, 1500,
            f"95th percentile response time during peak load too high: {percentile_95:.2f}ms")
        self.assertLess(max_response_time, 3000,
            f"Maximum response time during peak load too high: {max_response_time:.2f}ms")

class CacheEffectivenessTest(LoadTestCase):
    """Tests effectiveness of system caching under load."""

    def setUp(self):
        super().setUp()
        # Clear cache before tests
        cache.clear()

    def test_cache_hit_ratio(self):
        """Test cache effectiveness for frequently accessed data."""
        num_requests = 1000
        cache_hits = 0
        
        # Simulate repeated room availability checks
        search_date = timezone.now().date() + timedelta(days=1)
        
        for _ in range(num_requests):
            # Alternate between cached and uncached requests
            if _ % 2 == 0:
                # Clear cache for some requests to simulate cache misses
                cache.clear()
            
            start_time = time.time()
            response = self.client.get(
                reverse('available_rooms_list'),
                {'start_date': search_date.strftime('%Y-%m-%d'),
                 'length_of_stay': '1'}
            )
            response_time = (time.time() - start_time) * 1000
            
            # Consider it a cache hit if response time is significantly lower
            if response_time < 50:  # 50ms threshold for cached responses
                cache_hits += 1
        
        cache_hit_ratio = cache_hits / num_requests
        self.assertGreater(cache_hit_ratio, 0.4,
            f"Cache hit ratio too low: {cache_hit_ratio:.2f}")

class MixedWorkloadTest(LoadTestCase):
    """Tests system performance under mixed workload patterns."""

    def test_mixed_workload_performance(self):
        """Test system performance under mixed read/write workload."""
        num_users = 15
        test_duration = 180  # 3 minutes
        all_response_times = {'read': [], 'write': []}
        
        def run_mixed_workload(username):
            client = Client()
            client.login(username=f'staff{username}', password='staffpass123')
            
            start_time = time.time()
            while time.time() - start_time < test_duration:
                # Simulate user think time
                time.sleep(random.uniform(0.5, 2))
                
                # Determine operation type (80% read, 20% write)
                operation = random.choices(
                    ['read', 'write'],
                    weights=[0.8, 0.2],
                    k=1
                )[0]
                
                try:
                    start_op_time = time.time()
                    
                    if operation == 'read':
                        # Perform read operation
                        action = random.choice([
                            lambda: client.get(reverse('guest_list')),
                            lambda: client.get(reverse('room_list')),
                            lambda: client.get(
                                reverse('available_rooms_list'),
                                {'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                                 'length_of_stay': '1'}
                            )
                        ])
                        response = action()
                        all_response_times['read'].append(
                            (time.time() - start_op_time) * 1000
                        )
                    else:
                        # Perform write operation
                        action = random.choice([
                            # Create new guest
                            lambda: client.post(
                                reverse('guest_create'),
                                {
                                    'title': 'Mr',
                                    'first_name': self.fake.first_name(),
                                    'last_name': self.fake.last_name(),
                                    'phone_number': self.fake.phone_number(),
                                    'email': self.fake.email(),
                                    'address_line1': self.fake.street_address(),
                                    'city': self.fake.city(),
                                    'county': self.fake.county(),
                                    'postcode': self.fake.postcode()
                                }
                            ),
                            # Create new reservation
                            lambda: client.post(
                                reverse('reservation_create', args=[random.choice(self.guests).guest_id]),
                                {
                                    'room_number': random.choice(self.rooms).room_number,
                                    'start_of_stay': (timezone.now().date() + timedelta(days=random.randint(1, 30))).strftime('%Y-%m-%d'),
                                    'length_of_stay': random.randint(1, 7),
                                    'number_of_guests': random.randint(1, 4),
                                    'status_code': 'RE'
                                }
                            )
                        ])
                        response = action()
                        all_response_times['write'].append(
                            (time.time() - start_op_time) * 1000
                        )
                    
                    self.assertIn(response.status_code, [200, 201, 302])
                    
                except Exception as e:
                    print(f"Error in mixed workload test for user {username}: {str(e)}")
        
        # Start concurrent user sessions
        threads = []
        for i in range(num_users):
            thread = threading.Thread(target=run_mixed_workload, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all sessions to complete
        for thread in threads:
            thread.join()
        
        # Analyze performance metrics
        for op_type in ['read', 'write']:
            if all_response_times[op_type]:
                avg_time = statistics.mean(all_response_times[op_type])
                percentile_95 = statistics.quantiles(all_response_times[op_type], n=20)[-1]
                
                # Assert performance metrics
                if op_type == 'read':
                    self.assertLess(avg_time, 500,
                        f"Average read response time too high: {avg_time:.2f}ms")
                    self.assertLess(percentile_95, 1000,
                        f"95th percentile read response time too high: {percentile_95:.2f}ms")
                else:
                    self.assertLess(avg_time, 1000,
                        f"Average write response time too high: {avg_time:.2f}ms")
                    self.assertLess(percentile_95, 2000,
                        f"95th percentile write response time too high: {percentile_95:.2f}ms")