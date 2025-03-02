from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from hotel_app.models import Guest, RoomType, Room, Reservation
import logging

logger = logging.getLogger(__name__)

class UsabilityTestCase(TestCase):
    """Base class for usability tests with common setup."""
    
    def setUp(self):
        """Set up test data and configurations."""
        self.client = Client()
        
        # Create test user with manager permissions
        self.user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123'
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

        # Create test room type
        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )

        # Create test room
        self.room = Room.objects.create(
            room_number=101,
            room_type=self.room_type
        )

        # Create test guest
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
        self.client.login(username='manager', password='managerpass123')

class NavigationUsabilityTest(UsabilityTestCase):
    """Tests focused on navigation flow and accessibility."""

    def test_navigation_links_present(self):
        """Test that all main navigation links are present on the home page."""
        response = self.client.get(reverse('home'))
        content = response.content.decode()
        
        # Check for main navigation links
        self.assertIn('Guests', content)
        self.assertIn('Rooms', content)
        self.assertIn('Reservations', content)
        self.assertIn('Find Available Rooms', content)

    def test_breadcrumb_navigation(self):
        """Test navigation elements on reservation confirmation page."""
        # Create a reservation
        reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            number_of_guests=2,
            start_of_stay=timezone.now().date(),
            length_of_stay=3,
            status_code='RE'
        )

        # Check reservation confirmation page navigation
        response = self.client.get(reverse('reservation_confirmed', args=[reservation.reservation_id]))
        content = response.content.decode()

        # Verify navigation elements
        self.assertIn('Hotel Management', content)  # Brand/Home link
        self.assertIn('Reservations', content)  # Navigation link
        self.assertIn('Room Reserved', content)  # Page title
        self.assertIn('View Reservations', content)  # Back to list button

class FormUsabilityTest(UsabilityTestCase):
    """Tests focused on form usability and feedback."""

    def test_guest_form_validation_feedback(self):
        """Test that guest form provides clear validation feedback."""
        # Submit invalid guest data
        invalid_data = {
            'title': 'Invalid',  # Invalid title
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '123',  # Invalid phone number
            'email': 'invalid-email',  # Invalid email
            'address_line1': '123 Test St',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'INVALID'  # Invalid postcode
        }
        
        response = self.client.post(reverse('guest_create'), invalid_data)
        content = response.content.decode()
        
        # Check for specific validation messages
        self.assertIn('Select a valid choice', content)
        self.assertIn('Enter a valid email address', content)
        self.assertIn('Phone number must start with', content)
        self.assertIn('Please enter a valid UK postcode', content)

    def test_reservation_form_price_calculation(self):
        """Test that reservation form shows price calculations clearly."""
        # Start reservation process
        session = self.client.session
        session['selected_room_number'] = self.room.room_number
        session['selected_start_date'] = timezone.now().date().strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 3
        session['selected_guest_id'] = self.guest.guest_id
        session.save()

        response = self.client.get(reverse('reservation_create', args=[self.guest.guest_id]))
        content = response.content.decode()

        # Check for price calculation elements
        self.assertIn('Total Price', content)  # Price label
        self.assertIn('300.00', content)  # Total price (3 nights)
        self.assertIn('Number of Nights', content)  # Length of stay label
        self.assertIn('3', content)  # Number of nights
        self.assertIn('Amount Paid', content)  # Payment field

class AccessibilityTest(UsabilityTestCase):
    """Tests focused on accessibility features."""

    def test_form_label_associations(self):
        """Test that form fields have proper label associations."""
        response = self.client.get(reverse('guest_create'))
        content = response.content.decode()

        # Check for label-input associations with their corresponding input fields
        self.assertIn('label for="id_first_name"', content)
        self.assertIn('input type="text" name="first_name"', content)

        self.assertIn('label for="id_last_name"', content)
        self.assertIn('input type="text" name="last_name"', content)

        self.assertIn('label for="id_email"', content)
        self.assertIn('input type="text" name="email"', content)

        # Verify the labels have proper text content
        self.assertIn('First name', content)
        self.assertIn('Last name', content)
        self.assertIn('Email', content)

    def test_required_field_indicators(self):
        """Test that required fields are clearly marked."""
        response = self.client.get(reverse('guest_create'))
        content = response.content.decode()
        
        # Check for required field indicators
        self.assertIn('required', content.lower())
        self.assertIn('*', content)  # Common required field indicator

class ErrorHandlingTest(UsabilityTestCase):
    """Tests focused on error handling and user feedback."""

    def test_double_booking_error_message(self):
        """Test that double booking attempts show clear error messages."""
        start_date = timezone.now().date()

        # Create initial reservation
        first_reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('300.00'),
            amount_paid=Decimal('300.00'),
            number_of_guests=2,
            start_of_stay=start_date,
            length_of_stay=3,
            status_code='RE'
        )

        # Set up session data for second reservation
        session = self.client.session
        session['selected_room_number'] = self.room.room_number
        session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 2
        session['selected_guest_id'] = self.guest.guest_id
        session.save()

        # First get the form to ensure CSRF token
        self.client.get(reverse('reservation_create', args=[self.guest.guest_id]))

        # Now attempt the double booking
        response = self.client.post(reverse('reservation_create', args=[self.guest.guest_id]), {
            'guest': self.guest.guest_id,
            'room_number': self.room.room_number,
            'reservation_date_time': timezone.now(),
            'price': '200.00',
            'amount_paid': '200.00',
            'number_of_guests': 2,
            'start_of_stay': start_date,
            'length_of_stay': 2,
            'status_code': 'RE',
            'notes': 'Double booking attempt'
        })
        self.assertEqual(response.status_code, 200)  # Should stay on same page with error
        self.assertContains(response, 'This room is already booked for the entered dates')        

    def test_payment_validation_feedback(self):
        """Test that payment validation provides clear feedback."""
        start_date = timezone.now().date()

        # Set up session data
        session = self.client.session
        session['selected_room_number'] = self.room.room_number
        session['selected_start_date'] = start_date.strftime('%Y-%m-%d')
        session['selected_length_of_stay'] = 3
        session['selected_guest_id'] = self.guest.guest_id
        session.save()

        # First get the form to ensure CSRF token
        response = self.client.get(reverse('reservation_create', args=[self.guest.guest_id]))

        # Attempt invalid payment
        response = self.client.post(reverse('reservation_create', args=[self.guest.guest_id]), {
            'guest': self.guest.guest_id,
            'room_number': self.room.room_number,
            'reservation_date_time': timezone.now(),
            'price': '300.00',
            'amount_paid': '400.00',  # More than total price
            'number_of_guests': 2,
            'start_of_stay': start_date,
            'length_of_stay': 3,
            'status_code': 'RE',
            'notes': 'Invalid payment test'
        }, follow=True)

        # Check for clear payment error message
        content = response.content.decode()
        self.assertIn('payment amount cannot exceed', content.lower())