# The Views of the application
# - handles the web requests
# - prepares forms and data for display
# - validates submitted data and saves
# - controls the flow of the application by directing to other web pages

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, date, timedelta
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .permissions import IsManager  # customised permissions
from .serialisers import GuestSerialiser, ReservationSerialiser, RoomSerialiser, RoomTypeSerialiser
from . models import Guest, Reservation, Room, RoomType
from . filters import AvailableRoomFilter, GuestFilter, ReservationFilter
from . forms import LoginForm, GuestForm, ReservationForm, RoomForm, RoomTypeForm
import logging

# create a Logger for use anywhere in this code and configure it to write info messages (or higher) to the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#
# Login/Logout views
#

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')  # Already logged in so navigate to home page

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  # successful login, so redirect to home page
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('login')  # after logout, return to login page

#
# Home page views
#
@login_required
def home_view(request):   
    return render(request, 'home.html')

#
# Guest views
#

# Create
@login_required
def guest_create_view(request):
    mode = request.GET.get('mode', 'list')  # Get 'next' from query param
    if request.method == 'POST':
        form = GuestForm(request.POST)
        if form.is_valid():
            form.save()
            # use mode to determine which page to navigate to next
            if mode == 'selection':
                return redirect('available_rooms_guest_selection')
            else:
                return redirect('guest_list')
    else:
        form = GuestForm()        
    return render(request, 'guest_form.html', {'form':form, 'title':'Guest Registration'})

# List
@login_required
def guest_list_view(request):
    guests = Guest.objects.all()
    guest_filter = GuestFilter(request.GET, queryset=guests)
    return render(request, 'guest_list.html', {'filter': guest_filter})

# Update
@login_required
def guest_update_view(request, guest_id):
    guest = Guest.objects.get(guest_id=guest_id)
    if request.method == "POST":
        form = GuestForm(request.POST,instance=guest)
        if form.is_valid():
            form.save()
            return redirect('guest_list')
    else:
        form = GuestForm(instance=guest)

    return render(request, 'guest_form.html', {'form':form, 'title':'Edit Guest Details'})

# Delete
@login_required
def guest_delete_view(request, guest_id):
    guest = Guest.objects.get(guest_id = guest_id)
    if request.method == 'POST':
        guest.delete()
        return redirect('guest_list')
    return render(request, 'guest_confirm_delete.html', {'guest':guest})

#
# Available Rooms
#

# List
@login_required
def available_rooms_list_view(request):

    # see if the filter criteria has been passed in on the request or previously saved in the session.
    # If not, set it to defaults and store it in the session for next time

    # - Start date
    start_date = request.GET.get('start_date')
    if (not start_date):
        start_date = request.session.get('available_rooms_default_start_date', timezone.now().date().strftime('%Y-%m-%d')) # default to today

    # - length of stay
    length_of_stay = request.GET.get('length_of_stay')
    if (not length_of_stay):
        length_of_stay = request.session.get('available_rooms_default_length_of_stay', 1)  # default to 1 night

    # - room type
    room_type = request.GET.get('room_type')
    if (not room_type):
        room_type = request.session.get('available_rooms_default_room_type', '')  # default to empty (All types)

    # store the filter values in the session for next time
    request.session['available_rooms_default_start_date'] = start_date
    request.session['available_rooms_default_length_of_stay'] = length_of_stay
    request.session['available_rooms_default_room_type'] = room_type

    # initialise the room filter
    rooms = Room.objects.all()
    available_room_filter = AvailableRoomFilter(
        request.GET or {'start_date': start_date, 'length_of_stay': length_of_stay, 'room_type':room_type},
        queryset=rooms)
 
    # show the list page and give it the filter
    return render(request, 'available_rooms_list.html', {'filter': available_room_filter})


@login_required
def available_rooms_reserve_view(request, room_number):
    start_date = request.GET.get('start_date')
    length_of_stay = request.GET.get('length_of_stay')

    request.session['selected_room_number'] = room_number
    request.session['selected_start_date'] = start_date
    request.session['selected_length_of_stay'] = length_of_stay
    return redirect('available_rooms_guest_selection')

# Guest Selection for the reservation process
@login_required
def available_rooms_guest_selection_view(request):
    room_number = request.session.get('selected_room_number')
    start_date = request.session.get('selected_start_date')
    # Convert start_date to datetime object
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    length_of_stay = request.session.get('selected_length_of_stay')

    guests = Guest.objects.all()
    guest_filter = GuestFilter(request.GET, queryset=guests)
    return render(request, 'guest_selection.html', {
        'filter': guest_filter,
        'room_number': room_number,
        'start_date': start_date_obj,
        'length_of_stay': length_of_stay,
    })

#
# Reservation views
#


# Create a reservation
def reservation_create_view(request, guest_id):
    logger.info(f"reservation_create_view called guest_id: {guest_id}")

    # store the guest_id in the session
    request.session['selected_guest_id'] = guest_id

    # gather data for the form
    guest = Guest.objects.get(guest_id=guest_id)
    room_number = request.session.get('selected_room_number', -1)
    room = Room.objects.get(room_number=room_number)
    start_date = request.session.get('selected_start_date', date.today().strftime('%Y-%m-%d'))
    start_of_reservation = datetime.strptime(start_date, "%Y-%m-%d").date()
    length_of_stay = request.session.get('selected_length_of_stay', 1)
    price_for_stay = room.room_type.price * int(length_of_stay)

    logger.info(f"Selected guest = Guest Id: {guest_id}, Name: {guest.display_name}")
    logger.info(f"Selected room = {room.room_number}")
    logger.info(f"Selected start_date = {start_of_reservation}")
    logger.info(f"Price per night: {room.room_type.price}")
    logger.info(f"Length of stay: {length_of_stay}")
    logger.info(f"Price for stay: {price_for_stay}")

    # build initial data for the form
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
  
    # handle the form being submitted
    if request.method == 'POST':
        logger.info(f"Post message = {request.POST}")
        form = ReservationForm(request.POST, initial=initial_data)
        if form.is_valid():
            reservation = form.save()
            return redirect('reservation_confirmed', reservation_id=reservation.reservation_id)
        else:
            logger.info(f"Reservation form is not valid")
    else:
        # handle the Get request displaying the form
        form = ReservationForm(initial=initial_data)
    
    # build the context for the html page
    save_button_text = 'Create Reservation' # the save button text on the form depends on whether the form is being used for Reservation/Check-in/Check-out
    context = {
        'form': form,
        'title':'Create Reservation',
        'save_button_text':save_button_text,
    }
    
    # display the reservation form html page
    return render(request, 'reservation_form.html', context)


# 'Reservation confirmed view'
@login_required
def reservation_confirmed_view(request, reservation_id):
    # find the reservation using the id parameter
    reservation = Reservation.objects.get(reservation_id=reservation_id)
    # show the confirmation page
    return render(request, 'reservation_confirmed.html', {'reservation':reservation})


# List
@login_required
def reservation_list_view(request):
    # see if the filter criteria has been passed in on the request or previously saved in the session.
    # If not, set it to defaults and store it in the session for next time

    logger.info(f"Reservation List View - GET request = {request.GET}")

    # - Start date
    start_date = request.GET.get('start_date', None)
    if start_date is None:
        start_date = request.session.get('reservations_default_start_date', timezone.now().date().strftime('%Y-%m-%d')) # default to today

    # - end_date
    end_date = request.GET.get('end_date', None)
    if end_date is None:
        today_plus_two_weeks = datetime.now() + timedelta(weeks=2)
        end_date = request.session.get('reservations_default_end_date', today_plus_two_weeks.date().strftime('%Y-%m-%d')) # default to 2 weeks time

    # - last_name
    last_name = request.GET.get('last_name', None)
    if last_name is None:
        last_name = request.session.get('reservations_default_last_name', '')  # default to empty
    
    # - room_number
    room_number = request.GET.get('room_number', None)
    if room_number is None:
        room_number = request.session.get('reservations_default_room_number', '')  # default to empty

    # store the filter values in the session for next time
    request.session['reservations_default_start_date'] = start_date
    request.session['reservations_default_end_date'] = end_date
    request.session['reservations_default_last_name'] = last_name
    request.session['reservations_default_room_number'] = room_number

    # initialise the reservations filter
    reservations = Reservation.objects.all()
    reservation_filter = ReservationFilter(
        request.GET or {'start_date': start_date, 'end_date': end_date, 'last_name': last_name, 'room_number':room_number},
        queryset=reservations)
    
    # show the list page and give it the filter
    return render(request, 'reservation_list.html', {'filter': reservation_filter})


# Edit
def reservation_update_view(request, reservation_id):    
    # find the reservation using the id parameter
    reservation = Reservation.objects.get(reservation_id=reservation_id)
    guest = reservation.guest
    room = reservation.room_number

    # see if a status code parameter was set
    status_code = request.GET.get('status_code')
          
    if (status_code == "IN"):
        # check-in mode requred
        # update the reservation status to Checked-in ready for approval when the form displays
        reservation.status_code = "IN"
        # and set correct title/label
        title = 'Check-in a Reservation'
        save_button_text = 'Save Check-in'
    elif (status_code == "OT"):
        # check-out mode requred
        # update the reservation status to Checked-out ready for approval when the form displays
        reservation.status_code = "OT"
        # and set correct title/label
        title = 'Check-out a Reservation'
        save_button_text = 'Save Check-out'
    else:
        # default is edit mode
        title = 'Edit a Reservation'
        save_button_text = 'Update Reservation'

    if request.method == 'POST':
        print(request.POST)
        form = ReservationForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            return redirect('reservation_list')
        else:
            logger.info(f"Reservation form is not valid when edited")
    else:
        form = ReservationForm( instance=reservation)

    context = {
        'form': form,
        'title':title,
        'save_button_text':save_button_text,
    }
        
    return render(request, 'reservation_form.html', context)


# Delete
@login_required
def reservation_delete_view(request, reservation_id):
    reservation = Reservation.objects.get(reservation_id = reservation_id)
    if request.method == 'POST':
        reservation.delete()
        return redirect('reservation_list')
    return render(request, 'reservation_confirm_delete.html', {'reservation':reservation})


#
# Room views
#

# Create
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_create_view(request):
    if request.method == 'POST':
        form = RoomForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('room_list')
    else:
        form = RoomForm()
    return render(request, 'room_form.html', {'form':form})

# List
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_list_view(request):
    rooms = Room.objects.all()
    return render(request, 'room_list.html', {'rooms':rooms})

# Update
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_update_view(request, room_number):
    room = Room.objects.get(room_number=room_number)    
    if request.method == "POST":
        form = RoomForm(request.POST,instance=room)
        if form.is_valid():
            form.save()
            return redirect('room_list')
    else:
        form = RoomForm(instance=room)

    return render(request, 'room_form.html', {'form':form})

# Delete
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_delete_view(request, room_number):
    room = Room.objects.get(room_number = room_number)
    if request.method == 'POST':
        room.delete()
        return redirect('room_list')
    return render(request, 'room_confirm_delete.html', {'room':room})

#
# Room Type views
#

# Create
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_create_view(request):
    if request.method == 'POST':
        form = RoomTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('room_type_list')
        else:
            # Debugging: Print errors to the console
            print("Failed to save room_type")
            print(form.errors)  # Debugging: Print errors to the console
    else:
        form = RoomTypeForm()
    return render(request, 'room_type_form.html', {'form':form})

# List
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_list_view(request):
    room_types = RoomType.objects.all()
    return render(request, 'room_type_list.html', {'room_types':room_types})

# Update
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_update_view(request, room_type_code):    
    room_type = RoomType.objects.get(room_type_code = room_type_code)
    if request.method == "POST":
        form = RoomTypeForm(request.POST,instance=room_type)
        if form.is_valid():
            form.save()
            return redirect('room_type_list')
    else:
        form = RoomTypeForm(instance=room_type)

    return render(request, 'room_type_form.html', {'form':form})

# Delete
@login_required
@user_passes_test(lambda user: user.groups.filter(name='Manager').exists())
def room_type_delete_view(request, room_type_code):    
    room_type = RoomType.objects.get(room_type_code = room_type_code)
    if request.method == 'POST':
        room_type.delete()
        return redirect('room_type_list')
    return render(request, 'room_type_confirm_delete.html', {'room_type':room_type})

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


