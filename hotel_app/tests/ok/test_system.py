from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, datetime, timedelta

from hotel_app.models import Guest, RoomType, Room, Reservation
from hotel_app.forms import GuestForm, ReservationForm

class HotelSystemTestCase(TestCase):
    """System tests for end-to-end hotel management workflows"""
    
    def setUp(self):
        # Create test user with full permissions
        self.client = Client()
        self.user = User.objects.create_user(
            username='manager',
            email='manager@hotel.com',
            password='managerpass123'
        )
        
        # Add all necessary permissions
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
        self.standard_room = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )
        
        self.deluxe_room = RoomType.objects.create(
            room_type_code='DLX',
            room_type_name='Deluxe Room',
            price=Decimal('200.00'),
            deluxe=True,
            bath=True,
            separate_shower=True,
            maximum_guests=3
        )

        # Create rooms
        self.rooms = []
        for i in range(101, 104):  # Create 3 standard rooms
            self.rooms.append(Room.objects.create(
                room_number=i,
                room_type=self.standard_room
            ))
        
        for i in range(201, 203):  # Create 2 deluxe rooms
            self.rooms.append(Room.objects.create(
                room_number=i,
                room_type=self.deluxe_room
            ))

    def test_guest_reservation_and_stay_workflow(self):
        """Test complete guest journey from registration through checkout"""
        self.client.login(username='manager', password='managerpass123')
        
        # 1. Create new guest
        guest_data = {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone_number': '07123456789',
            'email': 'john.smith@example.com',
            'address_line1': '123 Main St',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }
        
        response = self.client.post(reverse('guest_create'), guest_data, follow=True)
        self.assertEqual(response.status_code, 200)
        
        guest = Guest.objects.get(email='john.smith@example.com')
        self.assertEqual(guest.first_name, 'John')

        # 2. Search for available rooms
        start_date = date.today() + timedelta(days=30)
        search_params = {
            'start_date': start_date.strftime('%Y-%m-%d'),
            'length_of_stay': 3,
            'room_type': 'STD'
        }
        
        response = self.client.get(reverse('available_rooms_list'), search_params)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '101')  # Should show standard room

        # 3. Make reservation
        session = self.client.session
        session['selected_room_number'] = self.rooms[0].room_number
        session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 3
        session.save()

        reservation_data = {
            'guest': guest.guest_id,
            'room_number': self.rooms[0].room_number,
            'guest_display': f"{guest.title} {guest.first_name} {guest.last_name}",
            'room_number_display': f"{self.rooms[0].room_number} - {self.rooms[0].room_type.room_type_name}",
            'reservation_date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '300.00',  # 3 nights at 100 per night
            'amount_paid': '300.00',
            'number_of_guests': 2,
            'start_of_stay': start_date.strftime('%Y-%m-%d'),
            'length_of_stay': 3,
            'status_code': 'RE',
            'notes': 'Test reservation'
        }

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guest.guest_id}),
            reservation_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # 4. Check-in
        reservation = Reservation.objects.get(guest=guest)
        check_in_data = reservation_data.copy()
        check_in_data['status_code'] = 'IN'

        response = self.client.post(
            reverse('reservation_update', kwargs={'reservation_id': reservation.reservation_id}),
            check_in_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify check-in
        reservation.refresh_from_db()
        self.assertEqual(reservation.status_code, 'IN')

        # 5. Check-out
        check_out_data = reservation_data.copy()
        check_out_data['status_code'] = 'OT'

        response = self.client.post(
            reverse('reservation_update', kwargs={'reservation_id': reservation.reservation_id}),
            check_out_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify check-out
        reservation.refresh_from_db()
        self.assertEqual(reservation.status_code, 'OT')

    def test_concurrent_reservations_and_room_availability(self):
        """Test handling of multiple concurrent reservations and room availability"""
        self.client.login(username='manager', password='managerpass123')
        
        # Create two guests
        guests = []
        guest_data = [
            {
                'title': 'Mr',
                'first_name': 'James',
                'last_name': 'Wilson',
                'phone_number': '07111222333',
                'email': 'james.wilson@example.com',
                'address_line1': '456 High St',
                'city': 'Manchester',
                'county': 'Greater Manchester',
                'postcode': 'M1 4BT'
            },
            {
                'title': 'Mrs',
                'first_name': 'Sarah',
                'last_name': 'Brown',
                'phone_number': '07444555666',
                'email': 'sarah.brown@example.com',
                'address_line1': '789 Park Rd',
                'city': 'Birmingham',
                'county': 'West Midlands',
                'postcode': 'B1 1AA'
            }
        ]
        
        for data in guest_data:
            response = self.client.post(reverse('guest_create'), data, follow=True)
            self.assertEqual(response.status_code, 200)
            guests.append(Guest.objects.get(email=data['email']))

        # Make overlapping reservations for different rooms
        start_date = date.today() + timedelta(days=45)
        
        # First reservation
        session = self.client.session
        session['selected_room_number'] = self.rooms[0].room_number
        session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 4
        session.save()

        reservation1_data = {
            'guest': guests[0].guest_id,
            'room_number': self.rooms[0].room_number,
            'guest_display': f"{guests[0].title} {guests[0].first_name} {guests[0].last_name}",
            'room_number_display': f"{self.rooms[0].room_number} - {self.rooms[0].room_type.room_type_name}",
            'reservation_date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '400.00',
            'amount_paid': '400.00',
            'number_of_guests': 2,
            'start_of_stay': start_date.strftime('%Y-%m-%d'),
            'length_of_stay': 4,
            'status_code': 'RE',
            'notes': 'First concurrent reservation'
        }

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guests[0].guest_id}),
            reservation1_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Second reservation - overlapping dates, different room
        session = self.client.session
        session['selected_room_number'] = self.rooms[3].room_number  # Deluxe room
        session['selected_start_date'] = (start_date + timedelta(days=2)).strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 3
        session.save()

        reservation2_data = {
            'guest': guests[1].guest_id,
            'room_number': self.rooms[3].room_number,
            'guest_display': f"{guests[1].title} {guests[1].first_name} {guests[1].last_name}",
            'room_number_display': f"{self.rooms[3].room_number} - {self.rooms[3].room_type.room_type_name}",
            'reservation_date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '600.00',
            'amount_paid': '600.00',
            'number_of_guests': 2,
            'start_of_stay': (start_date + timedelta(days=2)).strftime('%Y-%m-%d'),
            'length_of_stay': 3,
            'status_code': 'RE',
            'notes': 'Second concurrent reservation'
        }

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guests[1].guest_id}),
            reservation2_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        # Verify both reservations exist
        self.assertEqual(Reservation.objects.count(), 2)

        # Try to make conflicting reservation
        session = self.client.session
        session['selected_room_number'] = self.rooms[0].room_number
        session['selected_start_date'] = (start_date + timedelta(days=1)).strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 2
        session.save()

        conflicting_data = {
            'guest': guests[1].guest_id,
            'room_number': self.rooms[0].room_number,
            'guest_display': f"{guests[1].title} {guests[1].first_name} {guests[1].last_name}",
            'room_number_display': f"{self.rooms[0].room_number} - {self.rooms[0].room_type.room_type_name}",
            'reservation_date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '200.00',
            'amount_paid': '200.00',
            'number_of_guests': 1,
            'start_of_stay': (start_date + timedelta(days=1)).strftime('%Y-%m-%d'),
            'length_of_stay': 2,
            'status_code': 'RE',
            'notes': 'Conflicting reservation attempt'
        }

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guests[1].guest_id}),
            conflicting_data,
            follow=True
        )
        
        self.assertContains(response, 'This room is already booked for the entered dates')
        
        # Verify still only 2 reservations exist
        self.assertEqual(Reservation.objects.count(), 2)

    def test_payment_validation_and_status_transitions(self):
        """Test payment validation and reservation status transitions"""
        self.client.login(username='manager', password='managerpass123')
        
        # Create guest
        guest_data = {
            'title': 'Dr',
            'first_name': 'Emma',
            'last_name': 'Taylor',
            'phone_number': '07777888999',
            'email': 'emma.taylor@example.com',
            'address_line1': '321 Queen St',
            'city': 'Edinburgh',
            'county': 'Midlothian',
            'postcode': 'EH1 1AA'
        }
        
        response = self.client.post(reverse('guest_create'), guest_data, follow=True)
        self.assertEqual(response.status_code, 200)
        guest = Guest.objects.get(email='emma.taylor@example.com')

        start_date = date.today() + timedelta(days=60)
        
        # Try to create reservation with invalid payment (exceeding total)
        session = self.client.session
        session['selected_room_number'] = self.rooms[3].room_number  # Deluxe room
        session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 2
        session.save()

        invalid_payment_data = {
            'guest': guest.guest_id,
            'room_number': self.rooms[3].room_number,
            'guest_display': f"{guest.title} {guest.first_name} {guest.last_name}",
            'room_number_display': f"{self.rooms[3].room_number} - {self.rooms[3].room_type.room_type_name}",
            'reservation_date_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'price': '400.00',  # 2 nights at 200 per night
            'amount_paid': '500.00',  # More than total price
            'number_of_guests': 2,
            'start_of_stay': start_date.strftime('%Y-%m-%d'),
            'length_of_stay': 2,
            'status_code': 'RE',
            'notes': 'Invalid payment test'
        }

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guest.guest_id}),
            invalid_payment_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Payment amount cannot exceed the total price')

        # Create valid reservation
        valid_payment_data = invalid_payment_data.copy()
        valid_payment_data['amount_paid'] = '400.00'

        response = self.client.post(
            reverse('reservation_create', kwargs={'guest_id': guest.guest_id}),
            valid_payment_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        reservation = Reservation.objects.get(guest=guest)
        self.assertEqual(reservation.amount_paid, Decimal('400.00'))

        # Test status transitions
        # First check the initial status
        reservation.refresh_from_db()
        self.assertEqual(reservation.status_code, 'RE')  # Should start as Reserved

        # Valid status transitions
        # Reserved -> Checked In
        check_in_data = valid_payment_data.copy()
        check_in_data['status_code'] = 'IN'

        response = self.client.post(
            reverse('reservation_update', kwargs={'reservation_id': reservation.reservation_id}),
            check_in_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status_code, 'IN')

        # Checked In -> Checked Out
        check_out_data = valid_payment_data.copy()
        check_out_data['status_code'] = 'OT'

        response = self.client.post(
            reverse('reservation_update', kwargs={'reservation_id': reservation.reservation_id}),
            check_out_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status_code, 'OT')