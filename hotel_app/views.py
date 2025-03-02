"""
Hotel Management System Views

This module contains all the view functions for the hotel management application.
It handles:
- User authentication (login/logout)
- Guest management (CRUD operations)
- Room management (CRUD operations)
- Room type management (CRUD operations)
- Reservation management (booking, check-in, check-out)
- Room availability checking

Each view function is responsible for:
- Processing HTTP requests (GET/POST)
- Form handling and validation
- Data preparation for templates
- Business logic implementation
- Navigation flow control
"""

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.urls import reverse
from django.http import Http404
from datetime import datetime, date, timedelta
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .permissions import IsManager  # customised permissions
from .serialisers import GuestSerialiser, ReservationSerialiser, RoomSerialiser, RoomTypeSerialiser
from . models import Guest, Reservation, Room, RoomType
from . filters import AvailableRoomFilter, GuestFilter, ReservationFilter, RoomFilter
from . forms import LoginForm, GuestForm, ReservationForm, RoomForm, RoomTypeForm
import logging
import re

# Configure logging to write INFO level messages or higher to the terminal
# This provides detailed operation tracking for debugging and monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Authentication Views

def login_view(request):
    """
    Handle user authentication and login.

    This view manages the login process by:
    1. Checking if user is already authenticated
    2. Processing login form submission
    3. Authenticating credentials
    4. Creating user session on successful login

    Args:
        request: HttpRequest object containing user data and form submission

    Returns:
        HttpResponse: Renders login form or redirects to home page on success
    """
    logger.info(f"Login attempt from IP: {request.META.get('REMOTE_ADDR')}")

    if request.user.is_authenticated:
        logger.info(f"Already authenticated user {request.user.username} redirected to home")
        return redirect('home')  # User already logged in, redirect to home page

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            logger.info(f"Login form validation successful for user: {username}")
            user = authenticate(request, username=username, password=form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                logger.info(f"User {username} successfully logged in")
                return redirect('home')  # Successful login, redirect to home page
            else:
                logger.warning(f"Failed login attempt for user: {username}")
        else:
            logger.warning("Login form validation failed")
    else:
        form = LoginForm()  # Create empty form for GET request
        logger.info("Displaying empty login form")

    return render(request, "login.html", {"form": form})


@login_required
def logout_view(request):
    """
    Handle user logout.

    This view terminates the user's session and redirects to the login page.
    Protected by @login_required to ensure only authenticated users can logout.

    Args:
        request: HttpRequest object containing user session data

    Returns:
        HttpResponse: Redirects to login page after logging out
    """
    username = request.user.username
    logger.info(f"Logout initiated for user: {username}")
    logout(request)
    logger.info(f"User {username} successfully logged out")
    return redirect('login')

# Home Page View

@login_required
def home_view(request):
    """
    Display the main dashboard/home page of the hotel management system.

    This view serves as the landing page after login, showing different options
    based on user permissions. It checks if the user has manager privileges
    to potentially show additional management features.

    Args:
        request: HttpRequest object containing user session and permissions data

    Returns:
        HttpResponse: Renders the home page template

    Notes:
        - Protected by @login_required decorator
        - Checks for 'Manager' group membership for additional features
    """
    # Check if user belongs to the 'Manager' group for permission-based content
    is_manager = request.user.groups.filter(name='Manager').exists()

    return render(request, 'home.html')

# Guest Management Views

@login_required
def guest_create_view(request):
    """
    Create a new guest record in the system.

    This view handles both the display and processing of the guest registration form.
    It supports two modes of operation:
    - Standard mode: Returns to guest list after creation
    - Selection mode: Returns to guest selection page (used during reservation)

    Args:
        request: HttpRequest object containing form data and mode parameter

    Returns:
        HttpResponse: Renders guest form or redirects based on mode
    """
    mode = request.GET.get('mode', 'list')  # Get operation mode from query param
    logger.info(f"Guest creation initiated in {mode} mode by user: {request.user.username}")

    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            try:
                guest = form.save()
                logger.info(f"New guest created - ID: {guest.guest_id}, Name: {guest.display_name}")
                # Redirect based on operation mode
                if mode == 'selection':
                    logger.info(f"Redirecting to guest selection after creating guest {guest.guest_id}")
                    return redirect('available_rooms_guest_selection')
                else:
                    logger.info(f"Redirecting to guest list after creating guest {guest.guest_id}")
                    return redirect('guest_list')
            except ValidationError as e:
                logger.info(f"Validation error caught and added to the form")
                form.add_error(None, e)  # Attach model-level errors to the form
        else:
            logger.warning("Guest creation form validation failed")
            logger.info(f"Form errors: {form.errors}")
    else:
        form = GuestForm()
        logger.info("Displaying empty guest registration form")

    return render(request, 'guest_form.html', {
        'form': form,
        'title': 'Guest Registration'
    })


@login_required
def guest_list_view(request):
    """
    Display a filterable list of all guests with validation.

    This view shows all registered guests and provides filtering capabilities
    through the GuestFilter class. Users can search and filter guests based
    on various criteria with input validation.

    Args:
        request: HttpRequest object containing filter parameters

    Returns:
        HttpResponse: Renders guest list with filter form and any validation messages
    """
    # Initialize filter
    guest_filter = GuestFilter(request.GET, queryset=Guest.objects.all())

    # Validate filter inputs if any filters are applied
    validation_errors = []
    if request.GET:
        if 'postcode' in request.GET and request.GET['postcode']:
            is_valid, error = guest_filter.validate_postcode(request.GET['postcode'])
            if not is_valid:
                validation_errors.append(f"Invalid postcode format: {error}")

        if 'last_name' in request.GET and request.GET['last_name']:
            is_valid, error = guest_filter.validate_last_name(request.GET['last_name'])
            if not is_valid:
                validation_errors.append(f"Invalid last name format: {error}")

    # Add any validation errors to messages
    if validation_errors:
        from django.contrib import messages
        for error in validation_errors:
            messages.error(request, error)
        # Reset filter if there are validation errors
        guest_filter = GuestFilter(queryset=Guest.objects.all())

    return render(request, 'guest_list.html', {
        'filter': guest_filter
    })


@login_required
def guest_update_view(request, guest_id):
    """
    Update an existing guest's information.

    This view handles the editing of guest details, including validation
    and saving of the updated information.

    Args:
        request: HttpRequest object containing form data
        guest_id: Primary key of the guest to update

    Returns:
        HttpResponse: Renders edit form or redirects to list on success

    Raises:
        Guest.DoesNotExist: If guest_id is not found
    """
    logger.info(f"Guest update initiated for guest_id: {guest_id} by user: {request.user.username}")
    try:
        guest = Guest.objects.get(guest_id=guest_id)
        logger.info(f"Found guest to update: {guest.display_name}")

        if request.method == "POST":
            form = GuestForm(request.POST, instance=guest)
            if form.is_valid():
                try:
                    updated_guest = form.save()
                    logger.info(f"Successfully updated guest - ID: {updated_guest.guest_id}, Name: {updated_guest.display_name}")
                    return redirect('guest_list')
                except ValidationError as e:
                    logger.info(f"Validation error caught and added to the form")
                    form.add_error(None, e)  # Attach model-level errors to the form
            else:
                logger.warning(f"Guest update form validation failed for guest_id: {guest_id}")
                logger.info(f"Form errors: {form.errors}")
        else:
            form = GuestForm(instance=guest)
            logger.info(f"Displaying edit form for guest: {guest.display_name}")

        return render(request, 'guest_form.html', {
            'form': form,
            'title': 'Edit Guest Details'
        })
    except Guest.DoesNotExist:
        logger.error(f"Attempted to update non-existent guest with ID: {guest_id}")
        raise


@login_required
def guest_delete_view(request, guest_id):
    """
    Delete a guest record from the system.

    This view handles the confirmation and deletion of guest records.
    It requires a POST request for actual deletion to prevent accidental
    deletions through GET requests.

    Args:
        request: HttpRequest object
        guest_id: Primary key of the guest to delete

    Returns:
        HttpResponse: Renders confirmation page or redirects after deletion

    Raises:
        Guest.DoesNotExist: If guest_id is not found
    """
    logger.info(f"Guest deletion initiated for guest_id: {guest_id} by user: {request.user.username}")
    try:
        guest = Guest.objects.get(guest_id=guest_id)
        logger.info(f"Found guest to delete: {guest.display_name}")

        if request.method == 'POST':
            guest_name = guest.display_name  # Store name before deletion for logging
            guest.delete()
            logger.info(f"Successfully deleted guest - ID: {guest_id}, Name: {guest_name}")
            return redirect('guest_list')

        logger.info(f"Displaying delete confirmation page for guest: {guest.display_name}")
        return render(request, 'guest_confirm_delete.html', {'guest': guest})
    except Guest.DoesNotExist:
        logger.error(f"Attempted to delete non-existent guest with ID: {guest_id}")
        raise

# Room Availability Management Views

@login_required
def available_rooms_list_view(request):
    """
    Display a list of available rooms based on search criteria.

    This view handles the search for available rooms based on:
    - Check-in date
    - Length of stay
    - Room type preferences

    The view maintains search criteria in the session for user convenience
    and applies default values when criteria are not specified.

    Args:
        request: HttpRequest object containing search parameters

    Returns:
        HttpResponse: Renders available rooms list with filter form
    """
    logger.info(f"Available rooms search initiated by user: {request.user.username}")

    # Process start date parameter with session fallback
    start_date = request.GET.get('start_date')
    if not start_date:
        start_date = request.session.get(
            'available_rooms_default_start_date',
            timezone.now().date().strftime('%Y-%m-%d')  # Default to today
        )
        logger.info(f"Using default/session start date: {start_date}")
    else:
        logger.info(f"Using provided start date: {start_date}")

    # Process length of stay parameter with session fallback
    length_of_stay = request.GET.get('length_of_stay')
    if not length_of_stay:
        length_of_stay = request.session.get(
            'available_rooms_default_length_of_stay',
            1  # Default to 1 night
        )
        logger.info(f"Using default/session length of stay: {length_of_stay}")
    else:
        logger.info(f"Using provided length of stay: {length_of_stay}")

    # Process room type parameter with session fallback
    room_type = request.GET.get('room_type')
    if not room_type:
        room_type = request.session.get(
            'available_rooms_default_room_type',
            ''  # Default to all room types
        )
        logger.info("Using default/session room type: all types" if not room_type else f"Using default/session room type: {room_type}")
    else:
        logger.info(f"Using provided room type filter: {room_type}")

    # Persist search criteria in session for future use
    request.session['available_rooms_default_start_date'] = start_date
    request.session['available_rooms_default_length_of_stay'] = length_of_stay
    request.session['available_rooms_default_room_type'] = room_type
    logger.info("Search criteria persisted to session")

    # Apply filters to room queryset
    rooms = Room.objects.all()
    logger.info(f"Total rooms before filtering: {rooms.count()}")

    available_room_filter = AvailableRoomFilter(
        request.GET or {
            'start_date': start_date,
            'length_of_stay': length_of_stay,
            'room_type': room_type
        },
        queryset=rooms
    )

    filtered_rooms_count = len(available_room_filter.qs)
    logger.info(f"Available rooms after filtering: {filtered_rooms_count}")

    return render(request, 'available_rooms_list.html', {
        'filter': available_room_filter
    })


@login_required
def available_rooms_reserve_view(request, room_number):
    """
    Initiate the room reservation process.

    This view stores the selected room and stay details in the session
    before redirecting to guest selection. It acts as a bridge between
    room selection and guest assignment.

    Args:
        request: HttpRequest object containing stay details
        room_number: The selected room's identifier

    Returns:
        HttpResponse: Redirects to guest selection page
    """
    # Store reservation details in session
    request.session['selected_room_number'] = room_number
    request.session['selected_start_date'] = request.GET.get('start_date')
    request.session['selected_length_of_stay'] = request.GET.get('length_of_stay')

    return redirect('available_rooms_guest_selection')


@login_required
def available_rooms_guest_selection_view(request):
    """
    Display guest selection interface for room reservation.

    This view shows a filterable list of guests to associate with the
    selected room reservation. It retrieves reservation details from
    the session and presents them alongside the guest selection interface.

    Args:
        request: HttpRequest object

    Returns:
        HttpResponse: Renders guest selection page with reservation details

    Notes:
        Requires the following session data:
        - selected_room_number
        - selected_start_date
        - selected_length_of_stay
    """
    # Retrieve reservation details from session
    room_number = request.session.get('selected_room_number')
    start_date = request.session.get('selected_start_date')
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    length_of_stay = request.session.get('selected_length_of_stay')

    # Prepare guest selection interface
    guests = Guest.objects.all()
    guest_filter = GuestFilter(request.GET, queryset=guests)

    return render(request, 'guest_selection.html', {
        'filter': guest_filter,
        'room_number': room_number,
        'start_date': start_date_obj,
        'length_of_stay': length_of_stay,
    })

# Reservation Management Views

@login_required
def reservation_create_view(request, guest_id):
    """
    Create a new reservation for a specific guest.

    This view handles the creation of a new reservation by:
    1. Retrieving guest and room details from session/database
    2. Calculating stay duration and total price
    3. Preparing and processing the reservation form
    4. Handling form submission and validation

    Args:
        request: HttpRequest object containing session data
        guest_id: ID of the guest making the reservation

    Returns:
        HttpResponse: Renders reservation form or redirects to confirmation

    Raises:
        Guest.DoesNotExist: If guest_id is not found
        Room.DoesNotExist: If room_number from session is not found
    """
    logger.info(f"Reservation creation initiated for guest_id: {guest_id} by user: {request.user.username}")
    request.session['selected_guest_id'] = guest_id

    try:
        # Gather reservation details
        guest = Guest.objects.get(guest_id=guest_id)
        logger.info(f"Found guest for reservation: {guest.display_name}")

        room_number = request.session.get('selected_room_number', -1)
        logger.info(f"Retrieved room number from session: {room_number}")

        room = Room.objects.get(room_number=room_number)
        logger.info(f"Found room for reservation: Room {room.room_number} ({room.room_type.room_type_name})")

        # Process dates and calculate price
        start_date = request.session.get('selected_start_date',
                                       date.today().strftime('%Y-%m-%d'))
        start_of_reservation = datetime.strptime(start_date, "%Y-%m-%d").date()
        length_of_stay = request.session.get('selected_length_of_stay', 1)
        price_for_stay = room.room_type.price * int(length_of_stay)

        logger.info("Reservation details:")
        logger.info(f" - Guest: {guest.display_name} (ID: {guest_id})")
        logger.info(f" - Room: {room.room_number} ({room.room_type.room_type_name})")
        logger.info(f" - Check-in: {start_of_reservation}")
        logger.info(f" - Length of stay: {length_of_stay} nights")
        logger.info(f" - Price per night: £{room.room_type.price}")
        logger.info(f" - Total price: £{price_for_stay}")

        # Prepare initial form data
        initial_data = {
            'room_number': room,
            'start_of_stay': start_of_reservation,
            'guest': guest,
            'number_of_guests': 1,
            'length_of_stay': length_of_stay,
            'status_code': "RE",
            'reservation_date_time': datetime.now(),
            'price': price_for_stay,
            'amount_paid': 0,
        }

        if request.method == 'POST':
            logger.info("Processing reservation form submission")
            form = ReservationForm(request.POST, initial=initial_data)
            if form.is_valid():
                try:
                    logger.info("Reservation form validation successful")
                    reservation = form.save()
                    logger.info(f"Created new reservation - ID: {reservation.reservation_id}")
                    logger.info(f"Redirecting to confirmation page for reservation {reservation.reservation_id}")
                    return redirect('reservation_confirmed',
                                reservation_id=reservation.reservation_id)
                except ValidationError as e:
                    logger.info(f"Validation error caught and added to the form")
                    form.add_error(None, e)  # Attach model-level errors to the form
            else:
                logger.warning("Reservation form validation failed")
                logger.info(f"Form errors: {form.errors}")
        else:
            form = ReservationForm(initial=initial_data)
            logger.info("Displaying new reservation form with initial data")

        context = {
            'form': form,
            'title': 'Create Reservation',
            'save_button_text': 'Create Reservation',
        }

        return render(request, 'reservation_form.html', context)

    except Guest.DoesNotExist:
        logger.error(f"Attempted to create reservation for non-existent guest with ID: {guest_id}")
        raise
    except Room.DoesNotExist:
        logger.error(f"Attempted to create reservation with non-existent room number: {room_number}")
        raise


@login_required
def reservation_confirmed_view(request, reservation_id):
    """
    Display confirmation page for a successful reservation.

    Args:
        request: HttpRequest object
        reservation_id: ID of the confirmed reservation

    Returns:
        HttpResponse: Renders confirmation page with reservation details

    Raises:
        Reservation.DoesNotExist: If reservation_id is not found
    """
    logger.info(f"Accessing reservation confirmation for reservation_id: {reservation_id}")
    try:
        reservation = Reservation.objects.get(reservation_id=reservation_id)
        logger.info(f"Found reservation for guest: {reservation.guest.display_name}, "
                   f"Room: {reservation.room_number.room_number}, "
                   f"Check-in: {reservation.start_of_stay}")

        logger.info("Rendering reservation confirmation page")
        return render(request, 'reservation_confirmed.html',
                     {'reservation': reservation})
    except Reservation.DoesNotExist:
        logger.error(f"Attempted to access non-existent reservation ID: {reservation_id}")
        raise


@login_required
def reservation_list_view(request):
    """
    Display a filterable list of all reservations.

    This view provides a comprehensive list of reservations with filtering
    capabilities based on:
    - Date range (start and end dates)
    - Guest's last name
    - Room number

    The view maintains filter preferences in the session for user convenience
    and applies default values when filters are not specified.

    Args:
        request: HttpRequest object containing filter parameters

    Returns:
        HttpResponse: Renders reservation list with filter form
    """
    logger.info(f"Reservation list view accessed by user: {request.user.username}")
    logger.info(f"Filter parameters: {request.GET}")

    # Process start date with session fallback
    start_date = request.GET.get('start_date')
    if start_date is None:
        start_date = request.session.get(
            'reservations_default_start_date',
            timezone.now().date().strftime('%Y-%m-%d')  # Default to today
        )

    # Process end date with session fallback
    end_date = request.GET.get('end_date')
    if end_date is None:
        today_plus_two_weeks = datetime.now() + timedelta(weeks=2)
        end_date = request.session.get(
            'reservations_default_end_date',
            today_plus_two_weeks.date().strftime('%Y-%m-%d')  # Default to 2 weeks ahead
        )

    # Log access and filter parameters
    logger.info(f"Reservation list view accessed by user: {request.user.username}")
    logger.info(f"Filter parameters: {request.GET}")

    # Process guest name filter with session fallback
    last_name = request.GET.get('last_name')

    if last_name is None:
        last_name = request.session.get('reservations_default_last_name', '')
    elif last_name and not last_name.replace("'", "").replace("-", "").replace(" ", "").isalpha():
        logger.warning(f"Invalid last name format: {last_name}")
        messages.error(request, "Please enter a valid last name (letters, hyphens and apostrophes only)")

    # Validate dates
    try:
        if start_date:
            datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            datetime.strptime(end_date, '%Y-%m-%d')
            if start_date and end_date and start_date > end_date:
                logger.warning(f"Invalid date range: start_date {start_date} is after end_date {end_date}")
                messages.error(request, "Please ensure the end date is after the start date")
    except ValueError as e:
        if start_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', start_date):
            logger.warning(f"Invalid start date format: {start_date}")
            messages.error(request, "Please enter start date in YYYY-MM-DD format")
        if end_date and not re.match(r'^\d{4}-\d{2}-\d{2}$', end_date):
            logger.warning(f"Invalid end date format: {end_date}")
            messages.error(request, "Please enter end date in YYYY-MM-DD format")

    # Process room number filter with session fallback
    room_number = request.GET.get('room_number')
    if room_number is None:
        room_number = request.session.get('reservations_default_room_number', '')

    # Persist filter preferences in session
    request.session.update({
        'reservations_default_start_date': start_date,
        'reservations_default_end_date': end_date,
        'reservations_default_last_name': last_name,
        'reservations_default_room_number': room_number
    })

    # Apply filters to reservation queryset
    reservations = Reservation.objects.all()
    reservation_filter = ReservationFilter(
        request.GET or {
            'start_date': start_date,
            'end_date': end_date,
            'last_name': last_name,
            'room_number': room_number
        },
        queryset=reservations
    )

    # Validate room number if provided
    if room_number:
        try:
            room_num = int(room_number)
            if room_num <= 0 or room_num > 9999:
                logger.warning(f"Invalid room number value: {room_number}")
                messages.error(request, "Please enter a valid room number (1-9999)")
        except ValueError:
            logger.warning(f"Invalid room number format: {room_number}")
            messages.error(request, "Please enter a valid room number (numbers only)")

    # Prepare context
    context = {
        'filter': reservation_filter
    }

    return render(request, 'reservation_list.html', context)


@login_required
def reservation_update_view(request, reservation_id):
    """
    Update an existing reservation or change its status.

    This view handles multiple operations on a reservation:
    1. General reservation details update
    2. Guest check-in process
    3. Guest check-out process

    The operation mode is determined by the 'status_code' parameter:
    - No status_code: Regular reservation update
    - status_code="IN": Check-in process
    - status_code="OT": Check-out process

    Args:
        request: HttpRequest object containing form data and status code
        reservation_id: ID of the reservation to update

    Returns:
        HttpResponse: Renders update form or redirects to list on success

    Raises:
        Reservation.DoesNotExist: If reservation_id is not found
    """
    # Retrieve reservation and related objects
    reservation = Reservation.objects.get(reservation_id=reservation_id)
    guest = reservation.guest
    room = reservation.room_number

    # Determine operation mode from status code
    status_code = request.GET.get('status_code')

    if status_code == "IN":
        # Check-in mode: Update status and set form labels
        reservation.status_code = "IN"
        title = 'Check-in a Reservation'
        save_button_text = 'Save Check-in'
    elif status_code == "OT":
        # Check-out mode: Update status and set form labels
        reservation.status_code = "OT"
        title = 'Check-out a Reservation'
        save_button_text = 'Save Check-out'
    else:
        # Regular update mode
        title = 'Edit a Reservation'
        save_button_text = 'Update Reservation'

    if request.method == 'POST':
        # Process form submission
        logger.info(f"Processing reservation update: {request.POST}")
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            try:
                form.save()
                logger.info("Reservation updated successfully")
                return redirect('reservation_list')
            except ValidationError as e:
                logger.info(f"Validation error caught and added to the form")
                form.add_error(None, e)  # Attach model-level errors to the form
        else:
            logger.warning("Reservation update form validation failed")
            logger.info(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        # Display form for GET request
        form = ReservationForm(instance=reservation)

    context = {
        'form': form,
        'title': title,
        'save_button_text': save_button_text,
    }

    return render(request, 'reservation_form.html', context)


@login_required
def reservation_delete_view(request, reservation_id):
    """
    Delete an existing reservation.

    This view handles the deletion of reservations with a confirmation step:
    1. GET request: Shows confirmation page
    2. POST request: Performs the actual deletion

    Args:
        request: HttpRequest object
        reservation_id: ID of the reservation to delete

    Returns:
        HttpResponse: Renders confirmation page or redirects after deletion

    Raises:
        Reservation.DoesNotExist: If reservation_id is not found
    """
    reservation = Reservation.objects.get(reservation_id=reservation_id)

    if request.method == 'POST':
        # Actual deletion on POST request
        reservation.delete()
        return redirect('reservation_list')

    # Show confirmation page on GET request
    return render(request, 'reservation_confirm_delete.html',
                 {'reservation': reservation})


# Room Management Views

@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_create_view(request):
    """
    Create a new room in the hotel.

    This view handles the creation of new room records. It is restricted
    to users in the 'Manager' group for security purposes.

    Args:
        request: HttpRequest object containing form data

    Returns:
        HttpResponse: Renders room form or redirects to list on success

    Notes:
        - Requires login
        - Requires 'Manager' group membership
    """
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            try:
                room = form.save()
                logger.info(f"New room created - Number: {room.room_number}")
                messages.success(request, "Room created successfully.")
                return redirect('room_list')
            except ValidationError as e:
                logger.info(f"Validation error caught and added to the form")
                form.add_error(None, e)  # Attach model-level errors to the form
        else:
            logger.warning("Room creation form validation failed")
            logger.info(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = RoomForm()
        logger.info("Displaying empty room creation form")

    return render(request, 'room_form.html', {
        'form': form,
        'title': 'Create New Room'
    })


@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_list_view(request):
    """
    Display a list of all rooms in the hotel.

    This view shows all rooms and their current configurations.
    Access is restricted to managers only.

    Args:
        request: HttpRequest object

    Returns:
        HttpResponse: Renders room list page

    Notes:
        - Requires login
        - Requires 'Manager' group membership
    """
    logger.info(f"Room list view accessed by user: {request.user.username}")

    rooms = Room.objects.all().order_by('room_number')
    room_filter = RoomFilter(
        request.GET,
        queryset=rooms
    )
    rooms = room_filter.qs

    logger.info(f"Retrieved {rooms.count()} rooms after filtering")

    context = {
        'filter': room_filter,
        'rooms': rooms,
        'title': 'Room List'
    }
    return render(request, 'room_list.html', context)


@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_update_view(request, room_number):
    """
    Update an existing room's details.

    This view handles modifications to room configurations, including:
    - Room type assignment
    - Room status updates
    - Other room-specific settings

    Args:
        request: HttpRequest object containing form data
        room_number: Identifier of the room to update

    Returns:
        HttpResponse: Renders update form or redirects to list on success

    Raises:
        Room.DoesNotExist: If room_number is not found

    Notes:
        - Requires login
        - Requires 'Manager' group membership
    """
    logger.info(f"Room update initiated for number: {room_number} by user: {request.user.username}")

    try:
        room = Room.objects.get(room_number=room_number)
        logger.info(f"Found room {room_number} of type: {room.room_type.room_type_name}")

        if request.method == "POST":
            logger.info("Processing room update form submission")
            form = RoomForm(request.POST, instance=room)
            if form.is_valid():
                try:
                    updated_room = form.save()
                    logger.info(f"Successfully updated room {room_number}")
                    logger.info(f"New room type: {updated_room.room_type.room_type_name}, "
                            f"Status: {updated_room.status}")
                    messages.success(request, "Room updated successfully.")
                    return redirect('room_list')
                except ValidationError as e:
                    logger.info(f"Validation error caught and added to the form")
                    form.add_error(None, e)  # Attach model-level errors to the form
            else:
                logger.warning(f"Room update form validation failed")
                logger.info(f"Form errors: {form.errors}")
                messages.error(request, "Please correct the errors below.")
        else:
            form = RoomForm(instance=room)
            logger.info("Displaying room update form")

        context = {
            'form': form,
            'title': 'Update Room',
            'save_button_text': 'Update Room',
        }

        return render(request, 'room_form.html', context)
    except Room.DoesNotExist:
        logger.error(f"Attempted to update non-existent room number: {room_number}")
        raise Http404("Room not found")


@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_delete_view(request, room_number):
    """
    Delete a room from the hotel system.

    This view handles the removal of rooms with a confirmation step:
    1. GET request: Shows confirmation page
    2. POST request: Performs the actual deletion

    Args:
        request: HttpRequest object
        room_number: Identifier of the room to delete

    Returns:
        HttpResponse: Renders confirmation page or redirects after deletion

    Raises:
        Room.DoesNotExist: If room_number is not found

    Notes:
        - Requires login
        - Requires 'Manager' group membership
        - Should be used with caution as it permanently removes the room
    """
    logger.info(f"Room deletion initiated for room_number: {room_number} by user: {request.user.username}")
    try:
        room = Room.objects.get(room_number=room_number)
        logger.info(f"Found room to delete: {room.room_number} ({room.room_type.room_type_name})")

        if request.method == 'POST':
            room_info = f"Room {room.room_number} ({room.room_type.room_type_name})"  # Store info before deletion
            room.delete()
            logger.info(f"Successfully deleted {room_info}")
            return redirect('room_list')

        logger.info(f"Displaying delete confirmation page for room: {room.room_number}")
        return render(request, 'room_confirm_delete.html', {'room': room})
    except Room.DoesNotExist:
        logger.error(f"Attempted to delete non-existent room number: {room_number}")
        raise Http404("Room not found")

# Room Type Management Views

@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_create_view(request):
    """
    Create a new room type configuration.

    This view handles the creation of new room type categories, including:
    - Basic details (code, name)
    - Pricing information
    - Amenities and features
    - Capacity settings

    Args:
        request: HttpRequest object containing form data

    Returns:
        HttpResponse: Renders room type form or redirects to list on success

    Notes:
        - Requires login
        - Requires 'Manager' group membership
        - Validates room type code format
        - Logs form validation errors for debugging
    """
    logger.info(f"Room type creation initiated by user: {request.user.username}")

    if request.method == 'POST':
        form = RoomTypeForm(request.POST)
        if form.is_valid():
            try:
                room_type = form.save()
                logger.info(f"Created new room type: {room_type.room_type_name}, "
                        f"Price: {room_type.price}")
                messages.success(request, "Room type created successfully.")
                return redirect('room_type_list')
            except ValidationError as e:
                logger.info(f"Validation error caught and added to the form")
                form.add_error(None, e)  # Attach model-level errors to the form
        else:
            logger.warning("Room type creation form validation failed")
            logger.info(f"Form errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = RoomTypeForm()
        logger.info("Displaying empty room type creation form")

    context = {
        'form': form,
        'title': 'Create Room Type',
        'save_button_text': 'Create Room Type'
    }

    return render(request, 'room_type_form.html', context)


@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_list_view(request):
    """
    Display a list of all room types.

    This view shows all available room type configurations, including:
    - Type codes and names
    - Current pricing
    - Available amenities
    - Maximum capacity

    Args:
        request: HttpRequest object

    Returns:
        HttpResponse: Renders room type list page

    Notes:
        - Requires login
        - Requires 'Manager' group membership
        - Used for room type management and reference
    """
    logger.info(f"Room type list view accessed by user: {request.user.username}")

    room_types = RoomType.objects.all().order_by('room_type_name')
    logger.info(f"Retrieved {room_types.count()} room types")

    context = {
        'room_types': room_types,
        'title': 'Room Types'
    }
    return render(request, 'room_type_list.html', context)

@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_update_view(request, room_type_code):
    """
    Update an existing room type configuration.

    This view handles modifications to room type settings, including:
    - Basic information updates
    - Price adjustments
    - Amenity changes
    - Capacity modifications

    Args:
        request: HttpRequest object containing form data
        room_type_code: Unique code of the room type to update

    Returns:
        HttpResponse: Renders update form or redirects to list on success

    Raises:
        RoomType.DoesNotExist: If room_type_code is not found

    Notes:
        - Requires login
        - Requires 'Manager' group membership
        - Changes affect all rooms of this type
    """
    logger.info(f"Room type update initiated for code: {room_type_code} by user: {request.user.username}")

    try:
        room_type = RoomType.objects.get(room_type_code=room_type_code)
        logger.info(f"Found room type: {room_type.room_type_name}")

        if request.method == "POST":
            logger.info("Processing room type update form submission")
            form = RoomTypeForm(request.POST, instance=room_type)
            if form.is_valid():
                try:
                    updated_type = form.save()
                    logger.info(f"Successfully updated room type: {updated_type.room_type_name}")
                    logger.info(f"New price: {updated_type.price}, Max guests: {updated_type.maximum_guests}")
                    messages.success(request, "Room type updated successfully.")
                    return redirect('room_type_list')
                except ValidationError as e:
                    logger.info(f"Validation error caught and added to the form")
                    form.add_error(None, e)  # Attach model-level errors to the form
            else:
                logger.warning(f"Room type update form validation failed")
                logger.info(f"Form errors: {form.errors}")
                messages.error(request, "Please correct the errors below.")
        else:
            form = RoomTypeForm(instance=room_type)
            logger.info("Displaying room type update form")

        context = {
            'form': form,
            'title': 'Update Room Type',
            'save_button_text': 'Update Room Type'
        }

        return render(request, 'room_type_form.html', context)
    except RoomType.DoesNotExist:
        logger.error(f"Attempted to update non-existent room type code: {room_type_code}")
        raise Http404("Room type not found")


@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_delete_view(request, room_type_code):
    """
    Delete a room type from the system.

    This view handles the removal of room types with a confirmation step:
    1. GET request: Shows confirmation page
    2. POST request: Performs the actual deletion

    Args:
        request: HttpRequest object
        room_type_code: Unique code of the room type to delete

    Returns:
        HttpResponse: Renders confirmation page or redirects after deletion

    Raises:
        RoomType.DoesNotExist: If room_type_code is not found

    Notes:
        - Requires login
        - Requires 'Manager' group membership
        - Should be used with caution as it affects all rooms of this type
        - Consider impact on existing reservations before deletion
    """
    logger.info(f"Room type deletion initiated for code: {room_type_code} by user: {request.user.username}")
    try:
        room_type = RoomType.objects.get(room_type_code=room_type_code)
        logger.info(f"Found room type to delete: {room_type.room_type_name}")

        if request.method == 'POST':
            type_info = f"Room type {room_type.room_type_code} ({room_type.room_type_name})"  # Store info before deletion
            room_type.delete()
            logger.info(f"Successfully deleted {type_info}")
            return redirect('room_type_list')

        logger.info(f"Displaying delete confirmation page for room type: {room_type.room_type_name}")
        return render(request, 'room_type_confirm_delete.html',
                     {'room_type': room_type})
    except RoomType.DoesNotExist:
        logger.error(f"Attempted to delete non-existent room type code: {room_type_code}")
        raise Http404("Room type not found")

#
# Rest API suppport for each of the models
#
@api_view(['GET'])
def api_root(request, format=None):
    print("api_root was called!")  # Debugging line
    return Response({
        'guest': request.build_absolute_uri(reverse('api_guest_list_create')),
        'reservation': request.build_absolute_uri(reverse('api_reservation_list_create')),
        'room': request.build_absolute_uri(reverse('api_room_list_create')),
        'room-type': request.build_absolute_uri(reverse('api_room_type_list_create')),
    })

# Guest - list & create
class APIGuestListCreate(generics.ListCreateAPIView):
    # set style of authentication, requires either a logged in session (via admin tool or web site)
    # or the username & password sent in the request header
    authentication_classes = [SessionAuthentication, BasicAuthentication] 
    permission_classes = [IsAuthenticated]
    queryset = Guest.objects.all()
    serializer_class = GuestSerialiser

# Guest - retrieve, update, destroy
class APIGuestRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Guest.objects.all()
    serializer_class = GuestSerialiser
    lookup_field = 'pk' # accessed via primary key

# Reservation - list & create
class APIReservationListCreate(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerialiser

# Reservation - retrieve, update, destroy
class APIReservationRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerialiser
    lookup_field = 'pk' # accessed via primary key

# Room - list & create
class APIRoomListCreate(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsManager]  # Must be authenticated and have Manager access level
    queryset = Room.objects.all()
    serializer_class = RoomSerialiser

# Room - retrieve, update, destroy
class APIRoomRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsManager]  # Must be authenticated and have Manager access level
    queryset = Room.objects.all()
    serializer_class = RoomSerialiser
    lookup_field = 'pk' # accessed via primary key

# Room type - list & create
class APIRoomTypeListCreate(generics.ListCreateAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsManager]  # Must be authenticated and have Manager access level
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerialiser

# Room type - retrieve, update, destroy
class APIRoomTypeRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsManager]  # Must be authenticated and have Manager access level
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerialiser
    lookup_field = 'pk' # accessed via primary key