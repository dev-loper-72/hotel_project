from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Permission, Group
from django.core.exceptions import ValidationError
from decimal import Decimal

from hotel_app.models import Guest, RoomType, Room
from hotel_app.forms import GuestForm, RoomTypeForm


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

    def test_guest_delete_request(self):
        self.client.login(username='testuser', password='testpass123')
        # Verify the guest exists before deletion
        self.assertEqual(Guest.objects.count(), 1)
        # request the deletion page (will ask for confirmation)
        delete_url = reverse("guest_delete", args=[self.guest.guest_id])       
        response = self.client.get(delete_url)
        # checks the page response was successful and has used the correct template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_confirm_delete.html')   
        # confirm the deletion by submitting the form on the page
        response = self.client.post(delete_url, follow=True)  

        self.assertEqual(response.status_code, 200)  # Check successful response
        self.assertEqual(Guest.objects.count(), 0)  # Ensure guest has been deleted
        self.assertTemplateUsed(response, 'guest_list.html') # check that navigation has returned to the guest list page         


class GuestFormTestCase(TestCase):
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

class RoomTypeFormTest(TestCase):
    def test_valid_form(self):
        #Test if the form is valid when using valid data
        form_data = {
            'room_type_code': 'DOD',
            'room_type_name': 'Double Deluxe',
            'price': 125.00,
            'deluxe': True,
            'bath': True,
            'separate_shower': False,
            'maximum_guests': 4
        }
        form = RoomTypeForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_missing_required_fields(self):
        #Test form validation when required fields are missing
        form_data = {
            'room_type_code': None,
            'room_type_name': None,
            'price': None,
            'deluxe': False,
            'bath': False,
            'separate_shower': False,
            'maximum_guests': None
        }
        form = RoomTypeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('room_type_code', form.errors)
        self.assertIn('room_type_name', form.errors)
        self.assertIn('price', form.errors)
        self.assertIn('maximum_guests', form.errors)

    def test_invalid_data(self):
        #Test form validation for fields that could be left empty or contain incorrect data types
        form_data = {
            'room_type_code': '',
            'room_type_name': '',
            'price': 'invalid_price',  # Should be a number
            'deluxe': False, # Checkbox fields, can only be True/False anyway
            'bath': False,
            'separate_shower': False,
            'maximum_guests': 'five'  # Should be an number
        }
        form = RoomTypeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('room_type_code', form.errors)
        self.assertIn('room_type_name', form.errors)
        self.assertIn('price', form.errors)
        self.assertIn('maximum_guests', form.errors)
