from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date, datetime, timedelta

from hotel_app.models import Guest, RoomType, Room, Reservation
from hotel_app.forms import GuestForm, ReservationForm

class ViewsTestCase(TestCase):
    def setUp(self):
        # Create a test user
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Add necessary permissions to the user
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

    def test_home_view_redirect_when_not_logged_in(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)  # Expect redirect to login
        self.assertTrue(response.url.startswith('/login/'))

    def test_home_view_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_guest_list_view(self):
        self.client.login(username='testuser', password='testpass123')
        # First verify we can access the page
        response = self.client.get(reverse('guest_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_list.html')
        # Check for parts of the guest data that should appear in the table
        self.assertContains(response, 'John')
        self.assertContains(response, 'Smith')
        self.assertContains(response, 'SW1A 1AA')

    def test_room_list_view(self):
        # Make sure we're logged in
        self.client.login(username='testuser', password='testpass123')
        # Try to access the room list
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 200)

class FormTestCase(TestCase):
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

    def test_guest_form_valid(self):
        form = GuestForm(data=self.valid_guest_data)
        self.assertTrue(form.is_valid())

    def test_guest_form_invalid(self):
        invalid_data = self.valid_guest_data.copy()
        invalid_data['email'] = 'invalid-email'
        form = GuestForm(data=invalid_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

class RoomAvailabilityTestCase(TestCase):
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

    def test_room_price(self):
        # Test the room price value and type
        self.assertEqual(self.room.room_type.price, Decimal('100.00'))
        self.assertIsInstance(self.room.room_type.price, Decimal)

    def test_room_type_str(self):
        self.assertEqual(str(self.room_type), 'Standard Room')

    def test_room_str(self):
        # Test the string representation of a room
        self.assertEqual(str(self.room), '101')

class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create manager group with permissions
        self.manager_group = Group.objects.create(name='Manager')
        view_room_permission = Permission.objects.get(codename='view_room')
        self.manager_group.permissions.add(view_room_permission)

        self.staff_user = User.objects.create_user(username='staffuser', password='staffpass123')
        self.staff_user.groups.add(self.manager_group)

    def test_login_required(self):
        # Test accessing protected views without login
        guest_response = self.client.get(reverse('guest_list'))
        self.assertEqual(guest_response.status_code, 302)  # Should redirect to login

        room_response = self.client.get(reverse('room_list'))
        self.assertEqual(room_response.status_code, 302)  # Should redirect to login

        # Verify redirect URL contains login
        self.assertTrue(guest_response.url.startswith('/login/'))
        self.assertTrue(room_response.url.startswith('/login/'))

    def test_staff_permissions(self):
        # Test with regular user
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 302)  # Should redirect due to lack of manager permission

        # Test with manager user
        self.client.login(username='staffuser', password='staffpass123')
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 200)  # Should have access as manager