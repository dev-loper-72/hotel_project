"""
API test suite for the hotel application.

This module contains test cases for testing the REST API endpoints of the hotel application.
Tests cover CRUD operations for Guest, Reservation, Room, and RoomType models.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User, Group
from .models import Guest, Reservation, Room, RoomType
from datetime import datetime, timedelta

class APITestCase(TestCase):
    def setUp(self):
        """Set up test data and authenticate client."""
        # Create test user and add to Manager group
        self.user = User.objects.create_user(username='testmanager', password='testpass123')
        manager_group = Group.objects.create(name='Manager')
        self.user.groups.add(manager_group)
        
        # Set up API client
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # Create test data
        # Room Type
        self.room_type = RoomType.objects.create(
            room_type_code='TST',
            room_type_name='Test Room',
            price=100.00,
            maximum_guests=2,
            deluxe=False,
            bath=True,
            separate_shower=False
        )
        
        # Room
        self.room = Room.objects.create(
            room_number=101,
            room_type=self.room_type
        )
        
        # Guest
        self.guest = Guest.objects.create(
            title='Mr',
            first_name='John',
            last_name='Doe',
            phone_number='1234567890',
            email='john@test.com',
            address_line1='123 Test St',
            city='Test City',
            postcode='TE1 1ST'
        )
        
        # Reservation
        self.reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=datetime.now(),
            price=100.00,
            amount_paid=0.00,
            number_of_guests=1,
            start_of_stay=datetime.now().date(),
            length_of_stay=1,
            status_code='RE'
        )

    def test_guest_list(self):
        """Test GET request to guest list endpoint."""
        url = reverse('api_guest_list_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['first_name'], 'John')

    def test_guest_create(self):
        """Test POST request to create a new guest."""
        url = reverse('api_guest_list_create')
        data = {
            'title': 'Mrs',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone_number': '07123456789',  # Valid UK mobile number
            'email': 'jane@test.com',
            'address_line1': '456 Test Ave',
            'address_line2': '',  # Optional
            'city': 'London',  # Only letters allowed
            'county': 'Surrey',  # Required, only letters allowed
            'postcode': 'SW1A 1AA'  # Valid UK postcode format
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Guest.objects.count(), 2)
        self.assertEqual(Guest.objects.get(email='jane@test.com').first_name, 'Jane')

    def test_room_list(self):
        """Test GET request to room list endpoint."""
        url = reverse('api_room_list_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], 101)

    def test_room_type_create(self):
        """Test POST request to create a new room type."""
        url = reverse('api_room_type_list_create')
        data = {
            'room_type_code': 'DLX',
            'room_type_name': 'Deluxe Room',
            'price': 200.00,
            'deluxe': True,
            'bath': True,
            'separate_shower': True,
            'maximum_guests': 3
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(RoomType.objects.count(), 2)
        self.assertEqual(RoomType.objects.get(room_type_code='DLX').price, 200.00)

    def test_reservation_update(self):
        """Test PUT request to update a reservation."""
        url = reverse('api_reservation_update_destroy', args=[self.reservation.pk])
        data = {
            'guest': self.guest.pk,
            'room_number': self.room.pk,
            'reservation_date_time': datetime.now().isoformat(),
            'price': 150.00,
            'amount_paid': 50.00,
            'number_of_guests': 2,
            'start_of_stay': datetime.now().date().isoformat(),
            'length_of_stay': 2,
            'status_code': 'IN'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.price, 150.00)
        self.assertEqual(self.reservation.status_code, 'IN')

    def test_guest_delete(self):
        """Test DELETE request to remove a guest."""
        url = reverse('api_guest_update_destroy', args=[self.guest.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Guest.objects.count(), 0)

    def test_room_retrieve(self):
        """Test GET request to retrieve a specific room."""
        url = reverse('api_room_update_destroy', args=[self.room.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_number'], 101)
        self.assertEqual(response.data['room_type'], self.room_type.room_type_code)

    def test_room_type_list_filter(self):
        """Test GET request with filtering on room type list."""
        # Delete existing room types to start fresh
        RoomType.objects.all().delete()

        # Create test room type
        self.room_type = RoomType.objects.create(
            room_type_code='TST',
            room_type_name='Test Room',
            price=100.00,
            maximum_guests=2,
            deluxe=False,
            bath=True,
            separate_shower=False
        )

        # Create another room type with different price
        RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=80.00,
            maximum_guests=2,
            deluxe=False,
            bath=True,
            separate_shower=False
        )

        url = reverse('api_room_type_list_create')
        response = self.client.get(url + '?price=100.00')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_type_code'], 'TST')

    def test_reservation_create_validation(self):
        """Test validation when creating a reservation."""
        url = reverse('api_reservation_list_create')
        # Test with invalid data (missing required fields)
        data = {
            'guest': self.guest.pk,
            'room_number': self.room.pk,
            # Missing other required fields
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_access(self):
        """Test API access without authentication."""
        # Create a new unauthenticated client
        client = APIClient()
        client.force_authenticate(user=None)  # Explicitly remove authentication

        # Test multiple endpoints
        endpoints = [
            'api_guest_list_create',
            'api_room_list_create',
            'api_room_type_list_create',
            'api_reservation_list_create'
        ]

        for endpoint in endpoints:
            url = reverse(endpoint)
            response = client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_403_FORBIDDEN,
                f"Endpoint {endpoint} should return 403 for unauthenticated access"
            )