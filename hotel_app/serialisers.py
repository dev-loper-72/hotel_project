from rest_framework import serializers
from .models import Guest, Reservation, Room, RoomType

class GuestSerialiser(serializers.ModelSerializer):
     class Meta:
         model=Guest
         fields=['guest_id','title','first_name','last_name','phone_number','email',
                'address_line1','address_line2','city','county','postcode']

class ReservationSerialiser(serializers.ModelSerializer):
     class Meta:
         model=Reservation
         fields=['reservation_id','guest','room_number','reservation_date_time',
                 'price','amount_paid','number_of_guests','start_of_stay',
                 'length_of_stay','status_code','notes']

class RoomSerialiser(serializers.ModelSerializer):
     class Meta:
         model=Room
         fields=['room_number','room_type']

class RoomTypeSerialiser(serializers.ModelSerializer):
     class Meta:
         model=RoomType
         fields=['room_type_code','room_type_name', 'price','deluxe', 'bath', 'separate_shower', 'maximum_guests']

