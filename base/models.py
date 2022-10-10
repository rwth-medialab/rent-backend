from locale import DAY_1
from unittest.util import _MAX_LENGTH
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from datetime import date
from django.utils import timezone

class Priority(models.Model):
    prio = models.PositiveSmallIntegerField(verbose_name='priority in renting queue')
    name = models.CharField(max_length=100, verbose_name='name of the priority class')
    description = models.CharField(max_length=255, verbose_name='description of the priority class', null=True)

# extension of User model for addtitional information
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prio = models.ForeignKey(Priority, on_delete=models.CASCADE)
    authorized = models.BooleanField(verbose_name='authorized to rent objects')
    newsletter = models.BooleanField(verbose_name='newsletter signup')

# to categorize each RentalObjectType
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

# to cluster objects into a type
class RentalObjectType(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField(default='')
    # hide objects from rentalpage
    visible = models.BooleanField(default=False)
    image = models.ImageField()

# to show public information
class PublicInfoObjectType(models.Model):
    objecttype = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE)
    # infotype e.g. Warning danger (everything that works with bootstrap)
    type = models.CharField(max_length = 20, verbose_name='bootstrap type')
    content = models.TextField()

class RentalObject(models.Model):
    type = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE)
    # e.g. MaxLZ1 for MaxQDA license number 1
    internal_identifier = models.CharField(max_length=20)
    # if the object also got a external identifier e.g. a department uses its own identifiers but the objects also got a inventory number of the company
    inventory_number = models.CharField(max_length=100,null=True)
    # maybe broken so it shouldnt be rentable
    rentable = models.BooleanField(default=True)

class InternalInfoObjectType(models.Model):
    objecttype = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE)
    # infotype e.g. Warning danger (everything that works with bootstrap)
    type = models.CharField(max_length=20, verbose_name='bootstrap type')
    content = models.TextField()

# A rental Operation without a lender is a Reservation until someone gives out the correct object.
class RentalOperation(models.Model):
    object = models.ForeignKey(RentalObject, on_delete=models.CASCADE)
    renter = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='renter')
    lender = models.ForeignKey(User, blank=True, null=True, default=None, on_delete=models.CASCADE, related_name='lender')
    rejected = models.BooleanField()
    operation_number = models.BigIntegerField()
    reserved_at = models.DateTimeField(auto_now_add=True)
    reserved_from = models.DateTimeField()
    reserved_until = models.DateTimeField()
    picked_up_at = models.DateTimeField(null=True, default=None)
    handed_out_at = models.DateTimeField(null=True, default=None)
    received_back_at = models.DateTimeField(null=True, default=None)

# timeslots for corresponding 
class OnPremiseTimeSlot(models.Model):
    day = models.SmallIntegerField()
    start_time = models.TimeField()
    duration = models.DurationField()

# To block specific days e.g. someone is ill
class OnPremiseBlockedTimes(models.Model):
    starttime = models.DateTimeField(default=None, null=False)
    endtime = models.DateTimeField(default=None, null=False)

class OnPremiseBooking(models.Model):
    user = models.ForeignKey(User, on_delete= models.CASCADE)
    showed_up = models.BooleanField()
    start_datetime = models.DateTimeField()
    duration = models.DurationField()

class Notification(models.Model):
    type = models.CharField(max_length=100,default='email')
    receiver = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    added_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    send_at = models.DateTimeField(default=timezone.now)
    
# for general dynamic Settings like general lenting day and rocketchat url and email setup
class Settings(models.Model):
    type = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

# for suggestions which obejcts should be rented together
class Suggestion(models.Model):
    suggestion = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE, related_name='suggestion')
    suggestion_for = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE, related_name='suggestion_for')