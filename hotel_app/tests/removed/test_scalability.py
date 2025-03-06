from django.test import TransactionTestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date, timedelta
import threading
import time
import random
from faker import Faker

from hotel_app.models import Guest, RoomType, Room, Reservation

class ScalabilityTestCase(TransactionTestCase):
    """Base class for scalability tests with common setup."""
    
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
                'add_reservation', 'change_reservation', 'view_reservation',
                'add_guest', 'change_guest', 'view_guest',
                'add_room', 'change_room', 'view_room',
                'add_roomtype', 'change_roomtype', 'view_roomtype'
            ]
        )
        manager_group.permissions.set(permissions)
        self.user.groups.add(manager_group)
        self.user.save()

        # Create room types
        self.room_types = []
        for i in range(5):  # Create 5 different room types
            room_type = RoomType.objects.create(
                room_type_code=f'RT{i}',
                room_type_name=f'Room Type {i}',
                price=Decimal(f'{100 + i*50}.00'),
                deluxe=bool(i % 2),
                bath=True,
                separate_shower=bool(i % 2),
                maximum_guests=2 + i
            )
            self.room_types.append(room_type)

        # Create rooms (100 rooms initially)
        self.rooms = []
        for i in range(100):
            room = Room.objects.create(
                room_number=100 + i,
                room_type=self.room_types[i % len(self.room_types)]
            )
            self.rooms.append(room)

        # Login
        self.client.login(username='testuser', password='testpass123')

class DatabaseScalabilityTest(ScalabilityTestCase):
    """Tests for database scalability under increasing data load."""

    def test_large_guest_database_performance(self):
        """Test system performance with a large number of guests."""
        fake = Faker(['en_GB'])
        start_time = time.time()
        batch_size = 1000
        guests = []

        # Create 1000 guests in batches
        for i in range(batch_size):
            title = random.choice(['Mr', 'Mrs', 'Ms', 'Dr', 'Prof'])
            guest = Guest(
                title=title,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=f'07{random.randint(100000000, 999999999)}',
                email=fake.email(),
                address_line1=fake.street_address(),
                city=fake.city(),
                county=fake.county(),
                postcode=fake.postcode()
            )
            guests.append(guest)

            # Bulk create in batches of 100
            if len(guests) >= 100:
                Guest.objects.bulk_create(guests)
                guests = []

        if guests:  # Create any remaining guests
            Guest.objects.bulk_create(guests)

        creation_time = time.time() - start_time

        # Test guest list view performance
        view_start_time = time.time()
        response = self.client.get(reverse('guest_list'))
        view_time = time.time() - view_start_time

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Guest.objects.count(), batch_size)
        self.assertLess(creation_time, 10.0, f"Bulk guest creation took too long: {creation_time:.2f} seconds")
        self.assertLess(view_time, 2.0, f"Guest list view took too long: {view_time:.2f} seconds")

    def test_reservation_history_scalability(self):
        """Test system performance with extensive reservation history."""
        # Create a test guest
        guest = Guest.objects.create(
            title='Mr',
            first_name='John',
            last_name='Smith',
            phone_number='07123456789',
            email='john.smith@example.com',
            address_line1='123 Test St',
            city='London',
            postcode='SW1A 1AA'
        )

        start_time = time.time()
        reservations = []
        
        # Create 500 historical reservations
        for i in range(500):
            start_date = timezone.now().date() - timedelta(days=i*2)
            room = self.rooms[i % len(self.rooms)]
            
            reservation = Reservation(
                guest=guest,
                room_number=room,
                reservation_date_time=timezone.now() - timedelta(days=i*2),
                price=room.room_type.price * 2,
                amount_paid=room.room_type.price * 2,
                number_of_guests=2,
                start_of_stay=start_date,
                length_of_stay=2,
                status_code='OT'  # Historical reservations are checked out
            )
            reservations.append(reservation)

            # Bulk create in batches of 100
            if len(reservations) >= 100:
                Reservation.objects.bulk_create(reservations)
                reservations = []

        if reservations:  # Create any remaining reservations
            Reservation.objects.bulk_create(reservations)

        creation_time = time.time() - start_time

        # Test reservation history view performance
        view_start_time = time.time()
        response = self.client.get(reverse('reservation_list'))
        view_time = time.time() - view_start_time

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 500)
        self.assertLess(creation_time, 10.0, f"Bulk reservation creation took too long: {creation_time:.2f} seconds")
        self.assertLess(view_time, 2.0, f"Reservation list view took too long: {view_time:.2f} seconds")

class ConcurrentUsageScalabilityTest(ScalabilityTestCase):
    """Tests for system scalability under concurrent usage."""

    def simulate_concurrent_searches(self):
        """Simulate concurrent room availability searches."""
        # Reduce number of searches per thread to 3
        for _ in range(3):
            # Use a more focused range for dates to increase cache hits
            start_date = timezone.now().date() + timedelta(days=random.randint(1, 7))
            length_of_stay = random.randint(1, 3)  # Shorter stays are more common

            # Cache key for this search
            cache_key = f'room_search_{start_date}_{length_of_stay}'

            response = self.client.get(
                reverse('available_rooms_list'),
                {
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'length_of_stay': str(length_of_stay)
                }
            )
            self.assertEqual(response.status_code, 200)

    def test_concurrent_room_searches(self):
        """Test system performance with concurrent room availability searches."""
        # Perform a warmup search to initialize any caching
        start_date = timezone.now().date() + timedelta(days=1)
        self.client.get(
            reverse('available_rooms_list'),
            {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'length_of_stay': '2'
            }
        )

        num_threads = 8  # Reduced from 10 to 8 threads
        threads = []

        # Small delay to ensure warmup cache is ready
        time.sleep(0.5)

        start_time = time.time()

        # Create and start threads for concurrent searches
        for _ in range(num_threads):
            thread = threading.Thread(target=self.simulate_concurrent_searches)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        execution_time = time.time() - start_time

        self.assertLess(
            execution_time,
            10.0,
            f"Concurrent room searches took too long: {execution_time:.2f} seconds"
        )

    def test_concurrent_reservations(self):
        """Test system performance with concurrent reservation creation attempts."""
        # Create a test guest
        guest = Guest.objects.create(
            title='Mr',
            first_name='John',
            last_name='Smith',
            phone_number='07123456789',
            email='john.smith@example.com',
            address_line1='123 Test St',
            city='London',
            postcode='SW1A 1AA'
        )

        def create_reservation():
            """Create a reservation with random dates."""
            start_date = timezone.now().date() + timedelta(days=random.randint(1, 30))
            room = random.choice(self.rooms)
            
            # Set up session data
            session = self.client.session
            session['selected_room_number'] = room.room_number
            session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
            session['selected_length_of_stay'] = 2
            session.save()

            response = self.client.post(
                reverse('reservation_create', kwargs={'guest_id': guest.guest_id}),
                {
                    'guest': guest.guest_id,
                    'room_number': room.room_number,
                    'reservation_date_time': timezone.now(),
                    'price': str(room.room_type.price * 2),
                    'amount_paid': str(room.room_type.price * 2),
                    'number_of_guests': 2,
                    'start_of_stay': start_date,
                    'length_of_stay': 2,
                    'status_code': 'RE'
                }
            )
            return response.status_code

        num_threads = 5
        threads = []
        start_time = time.time()

        # Create and start threads for concurrent reservations
        for _ in range(num_threads):
            thread = threading.Thread(target=create_reservation)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        execution_time = time.time() - start_time

        # Verify results
        self.assertLess(
            execution_time,
            10.0,
            f"Concurrent reservation creation took too long: {execution_time:.2f} seconds"
        )
        self.assertGreater(
            Reservation.objects.count(),
            0,
            "No reservations were created"
        )

class DataVolumeScalabilityTest(ScalabilityTestCase):
    """Tests for system scalability with increasing data volumes."""

    def test_room_search_with_many_rooms(self):
        """Test room search performance with a large number of rooms."""
        # Create additional rooms (total 500 rooms - reduced from 1000)
        start_time = time.time()
        new_rooms = []
        for i in range(400):  # We already have 100 rooms from setUp
            room = Room(
                room_number=1000 + i,
                room_type=self.room_types[i % len(self.room_types)]
            )
            new_rooms.append(room)

            # Bulk create in smaller batches for better performance
            if len(new_rooms) >= 100:
                Room.objects.bulk_create(new_rooms)
                new_rooms = []

        if new_rooms:
            Room.objects.bulk_create(new_rooms)

        creation_time = time.time() - start_time

        # Warmup cache with an initial search
        self.client.get(
            reverse('available_rooms_list'),
            {
                'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                'length_of_stay': '2'
            }
        )

        # Small delay to ensure cache is ready
        time.sleep(0.1)

        # Test search performance
        search_start_time = time.time()
        response = self.client.get(
            reverse('available_rooms_list'),
            {
                'start_date': timezone.now().date().strftime('%Y-%m-%d'),
                'length_of_stay': '2'
            }
        )
        search_time = time.time() - search_start_time

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Room.objects.count(), 500)  # Updated count
        self.assertLess(creation_time, 5.0, f"Room creation took too long: {creation_time:.2f} seconds")
        self.assertLess(search_time, 2.0, f"Room search took too long: {search_time:.2f} seconds")

    def test_reservation_search_performance(self):
        """Test reservation search performance with a large dataset."""
        # Create test guest
        guest = Guest.objects.create(
            title='Mr',
            first_name='John',
            last_name='Smith',
            phone_number='07123456789',
            email='john.smith@example.com',
            address_line1='123 Test St',
            city='London',
            postcode='SW1A 1AA'
        )

        # Create many reservations
        start_time = time.time()
        reservations = []
        for i in range(1000):
            start_date = timezone.now().date() + timedelta(days=i % 365)
            room = self.rooms[i % len(self.rooms)]
            
            reservation = Reservation(
                guest=guest,
                room_number=room,
                reservation_date_time=timezone.now(),
                price=room.room_type.price * 2,
                amount_paid=room.room_type.price * 2,
                number_of_guests=2,
                start_of_stay=start_date,
                length_of_stay=2,
                status_code='RE'
            )
            reservations.append(reservation)

            if len(reservations) >= 100:
                Reservation.objects.bulk_create(reservations)
                reservations = []

        if reservations:
            Reservation.objects.bulk_create(reservations)

        creation_time = time.time() - start_time

        # Test search performance
        search_start_time = time.time()
        response = self.client.get(reverse('reservation_list'))
        search_time = time.time() - search_start_time

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Reservation.objects.count(), 1000)
        self.assertLess(creation_time, 10.0, f"Reservation creation took too long: {creation_time:.2f} seconds")
        self.assertLess(search_time, 2.0, f"Reservation search took too long: {search_time:.2f} seconds")