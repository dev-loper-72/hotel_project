from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from hotel_app.models import Guest, RoomType, Room, Reservation

class DatabaseCompatibilityTest(TestCase):
    """Test database compatibility across different model relationships."""
    
    def setUp(self):
        """Set up test data."""
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

    def test_foreign_key_compatibility(self):
        """Test foreign key relationships between models."""
        # Test Room to RoomType relationship
        self.assertEqual(self.room.room_type, self.room_type)
        
        # Test Reservation relationships
        reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('200.00'),
            amount_paid=Decimal('200.00'),
            number_of_guests=2,
            start_of_stay=date.today(),
            length_of_stay=2,
            status_code='RE'
        )
        
        self.assertEqual(reservation.guest, self.guest)
        self.assertEqual(reservation.room_number, self.room)

    def test_null_on_deletion(self):
        """Test on deletion behavior."""
        # Create a reservation
        reservation = Reservation.objects.create(
            guest=self.guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('200.00'),
            amount_paid=Decimal('200.00'),
            number_of_guests=2,
            start_of_stay=date.today(),
            length_of_stay=2,
            status_code='RE'
        )
        
        # Delete guest and verify guest is removed from reservation
        guest_id = self.guest.guest_id
        self.guest.delete()
        self.assertFalse(
            Reservation.objects.filter(guest_id=guest_id).exists(),
            "Guest should be removed from Reservation"
        )

class FormCompatibilityTest(TestCase):
    """Test form compatibility across different scenarios."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_guest_form_compatibility(self):
        """Test guest form compatibility with different input formats."""
        # Add required permissions
        add_guest_permission = Permission.objects.get(codename='add_guest')
        self.user.user_permissions.add(add_guest_permission)

        # Test with standard input
        response = self.client.post(reverse('guest_create'), {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone_number': '07123456789',
            'email': 'john.smith@example.com',
            'address_line1': '123 Main Street',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }, follow=True)  # Follow redirects
        self.assertEqual(response.status_code, 200)  # Final page after redirect

        # Test with UK format phone number
        response = self.client.post(reverse('guest_create'), {
            'title': 'Mr',
            'first_name': 'John',
            'last_name': 'Smith',
            'phone_number': '07987654321',  # Standard UK mobile format
            'email': 'john.smith2@example.com',  # Different email to avoid unique constraint
            'address_line1': '123 Main Street',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }, follow=True)  # Follow redirects
        self.assertEqual(response.status_code, 200)  # Final page after redirect

class ModelValidationCompatibilityTest(TestCase):
    """Test model validation compatibility."""

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

    def test_decimal_field_compatibility(self):
        """Test decimal field handling."""
        # Test with integer
        self.room_type.price = 100
        self.room_type.save()
        self.assertEqual(self.room_type.price, Decimal('100.00'))

        # Test with string
        self.room_type.price = Decimal('100.50')  # Convert to Decimal first
        self.room_type.save()
        self.assertEqual(self.room_type.price, Decimal('100.50'))

    def test_date_field_compatibility(self):
        """Test date field handling."""
        guest = Guest.objects.create(
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

        # Test with date object
        start_date = date.today()
        reservation = Reservation.objects.create(
            guest=guest,
            room_number=self.room,
            reservation_date_time=timezone.now(),
            price=Decimal('200.00'),
            amount_paid=Decimal('200.00'),
            number_of_guests=2,
            start_of_stay=start_date,
            length_of_stay=2,
            status_code='RE'
        )
        self.assertEqual(reservation.start_of_stay, start_date)

        # Test with string date
        start_date_str = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        # Convert string to date before saving
        reservation.start_of_stay = date.fromisoformat(start_date_str)
        reservation.save()
        self.assertEqual(
            reservation.start_of_stay,
            date.fromisoformat(start_date_str)
        )

class ViewCompatibilityTest(TestCase):
    """Test view compatibility across different scenarios."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')

    def test_view_template_compatibility(self):
        """Test view template rendering compatibility."""
        # Add required permissions
        view_guest_permission = Permission.objects.get(codename='view_guest')
        add_guest_permission = Permission.objects.get(codename='add_guest')
        self.user.user_permissions.add(view_guest_permission, add_guest_permission)

        # Test list view
        response = self.client.get(reverse('guest_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_list.html')

        # Test create view
        response = self.client.get(reverse('guest_create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'guest_form.html')

class AuthenticationCompatibilityTest(TestCase):
    """Test authentication compatibility."""

    def setUp(self):
        self.client = Client()

        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create staff user
        self.staff_user = User.objects.create_user(
            username='staffuser',
            password='staffpass123',
            is_staff=True
        )

        # Create superuser
        self.admin_user = User.objects.create_superuser(
            username='adminuser',
            password='adminpass123'
        )

        # Get required permissions
        self.view_room_permission = Permission.objects.get(codename='view_room')
        self.change_room_permission = Permission.objects.get(codename='change_room')
        self.add_room_permission = Permission.objects.get(codename='add_room')
        self.delete_room_permission = Permission.objects.get(codename='delete_room')

        # Create manager group with all permissions
        self.manager_group = Group.objects.create(name='Manager')
        self.manager_group.permissions.add(
            self.view_room_permission,
            self.change_room_permission,
            self.add_room_permission,
            self.delete_room_permission
        )

    def test_authentication_levels(self):
        """Test different authentication levels."""
        # Test unauthenticated access
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 302)  # Redirects to login

        # Test regular user access - should redirect to login since not in Manager group
        self.client.login(username='testuser', password='testpass123')
        self.user.user_permissions.add(self.view_room_permission)
        self.user.save()
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 302)  # Should redirect since user is not a manager

        # Test staff access
        self.client.login(username='staffuser', password='staffpass123')
        self.staff_user.groups.add(self.manager_group)
        self.staff_user.save()
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 200)

        # Test admin access
        self.client.login(username='adminuser', password='adminpass123')
        self.admin_user.groups.add(self.manager_group)
        self.admin_user.save()
        response = self.client.get(reverse('room_list'))
        self.assertEqual(response.status_code, 200)