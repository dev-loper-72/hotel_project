import unittest
from django.test import TestCase
from django_filters import FilterSet
from hotel_app.filters import GuestFilter
from hotel_app.models import Guest

class TestGuestFilter(TestCase):

    def setUp(self):
        # Create actual test database records
        self.guest1 = Guest.objects.create(
            last_name='Smith',
            postcode='SW1A 1AA',
            first_name='John',  # Required fields
            email='john@example.com',
            phone_number='1234567890'
        )
        self.guest2 = Guest.objects.create(
            last_name='Johnson',
            postcode='E1 6AN',
            first_name='Jane',
            email='jane@example.com',
            phone_number='0987654321'
        )
        self.guest3 = Guest.objects.create(
            last_name='smith',
            postcode='SW1A 2AA',
            first_name='James',
            email='james@example.com',
            phone_number='1122334455'
        )

    # Test Scenario 1: Test if GuestFilter is a subclass of django_filters.FilterSet.
    def test_guest_filter_is_subclass_of_filterset(self):
        self.assertTrue(issubclass(GuestFilter, FilterSet))

    # Test Scenario 2: Test filtering guests by last name using a case-insensitive search.
    def test_filter_guests_by_last_name_case_insensitive(self):
        filter_instance = GuestFilter({'last_name': 'smith'}, queryset=Guest.objects.all())
        filtered_guests = list(filter_instance.qs)
        self.assertEqual(len(filtered_guests), 2)
        self.assertIn(self.guest1, filtered_guests)
        self.assertIn(self.guest3, filtered_guests)
        self.assertNotIn(self.guest2, filtered_guests)

    # Test Scenario 3: Test filtering guests by postcode using partial matches.
    def test_filter_guests_by_postcode_partial_match(self):
        filter_instance = GuestFilter({'postcode': 'SW1A 1AA'}, queryset=Guest.objects.all())
        filtered_guests = list(filter_instance.qs)
        self.assertEqual(len(filtered_guests), 2)
        self.assertIn(self.guest1, filtered_guests)
        self.assertIn(self.guest3, filtered_guests)
        self.assertNotIn(self.guest2, filtered_guests)

    # Test Scenario 4: Test if the GuestFilter class correctly sets the model to Guest and includes the fields 'last_name' and 'postcode' in the Meta class.
    def test_guest_filter_meta_class(self):
        self.assertEqual(GuestFilter.Meta.model, Guest)
        self.assertListEqual(GuestFilter.Meta.fields, ['last_name', 'postcode'])

    # Test Scenario 5: Test if the GuestFilter correctly filters guests based on the last name and postcode fields.
    def test_guest_filter_correctly_filters_by_last_name_and_postcode(self):
        filter_instance = GuestFilter({'last_name': 'smith', 'postcode': 'SW1A 2AA'}, queryset=Guest.objects.all())
        filtered_guests = list(filter_instance.qs)
        self.assertEqual(len(filtered_guests), 1)
        self.assertNotIn(self.guest1, filtered_guests)
        self.assertIn(self.guest3, filtered_guests)
        self.assertNotIn(self.guest2, filtered_guests)

    # Test Scenario 6: Test if the 'fields' property in the GuestFilter class correctly includes 'last_name' and 'postcode'.
    def test_guest_filter_fields_property(self):
        self.assertIn('last_name', GuestFilter.Meta.fields)
        self.assertIn('postcode', GuestFilter.Meta.fields)

if __name__ == '__main__':
    unittest.main()