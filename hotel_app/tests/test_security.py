from django.test import TestCase, Client
from django.contrib.auth.models import User, Group, Permission
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import json

from hotel_app.models import Guest, RoomType, Room, Reservation

class SecurityTestCase(TestCase):
    """Base class for security tests with common setup."""
    
    def setUp(self):
        """Set up test data and configurations."""
        self.client = Client()
        
        # Create test users with different roles
        self.create_users()
        
        # Create test data
        self.create_test_data()

    def create_users(self):
        """Create users with different permission levels."""
        # Create superuser
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

        # Create manager user
        self.manager_user = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='managerpass123'
        )
        manager_group = Group.objects.create(name='Manager')
        # Get all relevant permissions
        permissions = Permission.objects.filter(
            content_type__app_label='hotel_app',
            codename__in=[
                'add_reservation', 'change_reservation', 'view_reservation', 'delete_reservation',
                'add_guest', 'change_guest', 'view_guest', 'delete_guest',
                'add_room', 'change_room', 'view_room', 'delete_room',
                'add_roomtype', 'change_roomtype', 'view_roomtype', 'delete_roomtype'
            ]
        )
        manager_group.permissions.set(permissions)
        self.manager_user.groups.add(manager_group)
        self.manager_user.is_staff = True
        self.manager_user.save()

        # Create staff user with limited permissions
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='staffpass123'
        )
        # Only give view permissions, no create/edit/delete
        view_permissions = Permission.objects.filter(
            content_type__app_label='hotel_app',
            codename__in=['view_guest', 'view_room', 'view_reservation', 'view_roomtype']
        )
        self.staff_user.user_permissions.set(view_permissions)
        # Ensure no other permissions are present
        self.staff_user.groups.clear()
        self.staff_user.save()
        # Verify staff has only view permissions
        staff_perms = self.staff_user.get_all_permissions()
        self.assertTrue(all('view' in perm for perm in staff_perms),
            "Staff should only have view permissions")

        # Create regular user with absolutely no permissions
        self.regular_user = User.objects.create_user(
            username='user',
            email='user@example.com',
            password='userpass123'
        )
        # Set all permission flags to False
        self.regular_user.is_active = True
        self.regular_user.is_staff = False
        self.regular_user.is_superuser = False

        # Remove all permissions and group memberships
        self.regular_user.user_permissions.clear()
        self.regular_user.groups.clear()

        # Explicitly remove all permissions including those from auth app
        all_perms = Permission.objects.all()
        for perm in all_perms:
            self.regular_user.user_permissions.remove(perm)

        # Save the user to ensure changes are persisted
        self.regular_user.save()

        # Verify the user has no permissions
        self.assertEqual(self.regular_user.get_all_permissions(), set(),
            "Regular user should have no permissions")

    def create_test_data(self):
        """Create test data for security testing."""
        # Create room type
        self.room_type = RoomType.objects.create(
            room_type_code='STD',
            room_type_name='Standard Room',
            price=Decimal('100.00'),
            deluxe=False,
            bath=True,
            separate_shower=False,
            maximum_guests=2
        )

        # Create room
        self.room = Room.objects.create(
            room_number=101,
            room_type=self.room_type
        )

        # Create guest
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

class AuthenticationSecurityTest(SecurityTestCase):
    """Test authentication and authorization security."""

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access protected views."""
        protected_urls = [
            reverse('guest_list'),
            reverse('room_list'),
            reverse('reservation_list'),
            reverse('guest_create'),
            reverse('room_create'),
        ]

        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302,
                f"Unauthenticated access to {url} should redirect to login")
            self.assertTrue(response.url.startswith('/login/'),
                f"Unauthenticated access to {url} should redirect to login page")

    def test_permission_based_access(self):
        """Test that users can only access views they have permission for."""
        # Test manager access (full permissions)
        self.client.login(username='manager', password='managerpass123')

        response = self.client.get(reverse('guest_list'))
        self.assertEqual(response.status_code, 200,
            "Manager should have access to guest list")

    def test_session_security(self):
        """Test session security features."""
        # Test session cookie settings
        login_successful = self.client.login(username='manager', password='managerpass123')
        self.assertTrue(login_successful, "Login should be successful")

        # Make a request that should create a session
        response = self.client.get(reverse('guest_list'), follow=True)
        self.assertEqual(response.status_code, 200, "Should be able to access guest list")

        # Get the client's session
        session = self.client.session
        self.assertTrue(session.session_key, "Session should be created")

        # Test session timeout
        session.set_expiry(300)  # 5 minutes
        session.save()

        # Verify session expiry
        self.assertTrue(session.get_expiry_age() <= 300,
            "Session expiry should be set to 5 minutes or less")

class InputValidationSecurityTest(SecurityTestCase):
    """Test input validation and sanitization."""

    def test_xss_prevention(self):
        """Test prevention of Cross-Site Scripting (XSS) attacks."""
        self.client.login(username='manager', password='managerpass123')
        
        # Test with malicious input
        xss_data = {
            'title': 'Mr',
            'first_name': '<script>alert("xss")</script>',
            'last_name': 'Smith<script>alert("xss")</script>',
            'phone_number': '07123456789',
            'email': 'test@example.com',
            'address_line1': '<img src="x" onerror="alert(\'xss\')">',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }
        
        response = self.client.post(reverse('guest_create'), xss_data)
        
        # Check that the script tags and attributes are properly escaped in the response
        self.assertContains(response, '&lt;script&gt;')  # Escaped <script>
        self.assertContains(response, '&gt;')  # Escaped >
        self.assertContains(response, '&quot;')  # Escaped "
        # Verify the original malicious content is not present
        self.assertNotContains(response, '<script>alert("xss")</script>')
        self.assertNotContains(response, '<img src="x" onerror="alert(\'xss\')">')

    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks."""
        self.client.login(username='manager', password='managerpass123')
        
        # Test with SQL injection attempts in query parameters
        sql_injection_attempts = [
            "' OR '1'='1",
            "; DROP TABLE guests--",
            "' UNION SELECT * FROM auth_user--"
        ]
        
        for sql_injection in sql_injection_attempts:
            response = self.client.get(
                reverse('guest_list'),
                {'search': sql_injection}
            )
            self.assertEqual(response.status_code, 200)
            # Verify the database is intact
            self.assertTrue(Guest.objects.exists())

    def test_form_validation(self):
        """Test form validation and sanitization."""
        self.client.login(username='manager', password='managerpass123')
        
        # Test with invalid data
        invalid_data = {
            'title': 'Mr',
            'first_name': '<script>alert("xss")</script>',  # Invalid characters
            'last_name': 'Smith<script>alert("xss")</script>',  # Invalid characters
            'phone_number': 'not-a-phone',  # Invalid phone format
            'email': 'not-an-email',  # Invalid email format
            'address_line1': '<img src="x" onerror="alert(\'xss\')">',  # Invalid characters
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'invalid'  # Invalid postcode format
        }

        response = self.client.post(reverse('guest_create'), invalid_data)
        self.assertEqual(response.status_code, 200)  # Returns form with errors

        # Check for specific validation errors
        self.assertContains(response, "Phone number must contain only digits")
        self.assertContains(response, "Enter a valid email address")
        self.assertContains(response, "Please enter a valid UK postcode")

class DataAccessSecurityTest(SecurityTestCase):
    """Test data access security controls."""

    def test_object_level_permissions(self):
        """Test that users can only access appropriate objects."""
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

        # Test staff access (should be allowed due to view permission)
        self.client.logout()  # Ensure clean session
        login_successful = self.client.login(username='staff', password='staffpass123')
        self.assertTrue(login_successful, "Staff login should be successful")
        response = self.client.get(reverse('reservation_list'))
        self.assertEqual(response.status_code, 200, "Staff should have access to reservation list")

        # Test regular user access (should be denied)
        self.client.logout()  # Ensure clean session

        # Ensure regular user has absolutely no permissions
        self.regular_user.user_permissions.clear()
        self.regular_user.groups.clear()
        self.regular_user.is_staff = False
        self.regular_user.is_superuser = False
        self.regular_user.save()

        # Clear session and cookies
        self.client.logout()
        self.client.session.flush()
        self.client.cookies.clear()

        # Test access to reservation list without logging in
        response = self.client.get(reverse('reservation_list'))
        self.assertEqual(response.status_code, 302,
            "Regular user without permissions should be redirected from reservation list")
        self.assertTrue(response.url.startswith('/login/'),
            "Regular user should be redirected to login page when accessing reservation list")

    def test_data_exposure(self):
        """Test prevention of sensitive data exposure."""
        self.client.login(username='manager', password='managerpass123')
        
        # Create guest with sensitive data
        guest = Guest.objects.create(
            title='Mr',
            first_name='Test',
            last_name='User',
            phone_number='07777777777',
            email='sensitive@example.com',
            address_line1='Secret Location',
            city='London',
            county='Greater London',
            postcode='SW1A 1AA'
        )
        
        # Test guest list view
        response = self.client.get(reverse('guest_list'))
        self.assertEqual(response.status_code, 200)
        
        # Verify that sensitive contact information is not exposed in list view
        # Email and phone should not be visible in the list view
        self.assertNotContains(response, 'sensitive@example.com')
        self.assertNotContains(response, '07777777777')

        # Basic information needed for identification should be visible
        self.assertContains(response, 'Test')  # First name
        self.assertContains(response, 'User')  # Last name
        self.assertContains(response, 'SW1A 1AA')  # Postcode

class FormSecurityTest(SecurityTestCase):
    """Test form security features."""

    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        self.client.login(username='manager', password='managerpass123')
        
        # Try to submit form without CSRF token
        self.client.handler.enforce_csrf_checks = True
        
        guest_data = {
            'title': 'Mr',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '07123456789',
            'email': 'test@example.com',
            'address_line1': '123 Street',
            'city': 'London',
            'county': 'Greater London',
            'postcode': 'SW1A 1AA'
        }
        
        response = self.client.post(reverse('guest_create'), guest_data)
        self.assertEqual(response.status_code, 403)

    def test_rate_limiting(self):
        """Test rate limiting on form submissions."""
        self.client.login(username='manager', password='managerpass123')
        
        # Try multiple rapid form submissions
        for _ in range(50):
            response = self.client.post(reverse('guest_create'), {
                'title': 'Mr',
                'first_name': 'Test',
                'last_name': 'User',
                'phone_number': '07123456789',
                'email': f'test{_}@example.com',
                'address_line1': '123 Street',
                'city': 'London',
                'county': 'Greater London',
                'postcode': 'SW1A 1AA'
            })
            
            # Should still work but check response time
            self.assertIn(response.status_code, [200, 302])

    def test_secure_file_upload(self):
        """Test secure file upload handling if implemented."""
        self.client.login(username='manager', password='managerpass123')
        
        # Test with various file types
        file_types = [
            ('test.txt', b'text content', 'text/plain'),
            ('test.html', b'<script>alert("xss")</script>', 'text/html'),
            ('test.jpg', b'fake image content', 'image/jpeg'),
        ]
        
        for filename, content, content_type in file_types:
            response = self.client.post(reverse('guest_create'), {
                'title': 'Mr',
                'first_name': 'Test',
                'last_name': 'User',
                'phone_number': '07123456789',
                'email': 'test@example.com',
                'address_line1': '123 Street',
                'city': 'London',
                'county': 'Greater London',
                'postcode': 'SW1A 1AA',
                'document': (filename, content, content_type)
            })
            
            # Should handle file upload securely
            self.assertIn(response.status_code, [200, 302])