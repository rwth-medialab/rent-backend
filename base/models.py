from locale import DAY_1
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from datetime import date
from django.utils import timezone


class Priority(models.Model):
    prio = models.PositiveSmallIntegerField(
        verbose_name='priority in renting queue')
    name = models.CharField(
        max_length=100, verbose_name='name of the priority class')
    description = models.CharField(
        max_length=255, verbose_name='description of the priority class', null=True)

    def __str__(self) -> str:
        return self.name + ": " + str(self.prio)


class Profile(models.Model):
    """
    extension of User model for addtitional information
    """
    class Meta:
        permissions = [
            ("inventory_editing",
             "able to edit and create the inventory and got nearly full access"),
            ("general_access", "got general Access to everything, but no editing rights"),
            ("lending_access", "is able to lend stuff")
        ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prio = models.ForeignKey(Priority, on_delete=models.CASCADE, default=Priority.objects.get_or_create(
        prio=99, name='Default', description='default class')[0].id)
    authorized = models.BooleanField(
        verbose_name='authorized to rent objects', default=False)
    newsletter = models.BooleanField(
        verbose_name='newsletter signup', default=False)

    def __str__(self) -> str:
        return self.user.username


class Category(models.Model):
    """
    To categorize each RentalObjectType
    """
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self) -> str:
        return self.name


class RentalObjectType(models.Model):
    """
    Parenttype for objects
    """
    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_id_prefix',
                fields=['prefix_identifier']
            )
        ]
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='rentalobjecttypes')
    shortdescription = models.TextField(default='')
    description = models.TextField(default='')
    manufacturer = models.CharField(max_length=100, default='')
    # hide objects from rentalpage
    visible = models.BooleanField(default=False)
    image = models.ImageField(default='nopicture.png')
    prefix_identifier = models.CharField(max_length=20, default="LZ")
    tags = models.ManyToManyField(Tag, blank=True)

    def __str__(self) -> str:
        return self.name


class ObjectTypeInfo(models.Model):
    """
    to show public information about an objectType
    """
    object_type = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE)
    # infotype e.g. Warning danger (everything that works with material)
    type = models.CharField(max_length=20, verbose_name='material type')
    public = models.BooleanField()
    order = models.IntegerField()
    content = models.TextField()


class RentalObject(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(name='unique_identifier', fields=[
                                    'type', 'internal_identifier'])
        ]
    type = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE, related_name='rentalobjects')
    # if the object also got a external identifier e.g. a department uses its own identifiers but the objects also got a inventory number of the company
    inventory_number = models.CharField(max_length=100, null=True, blank=True)
    # maybe broken so it shouldnt be rentable
    rentable = models.BooleanField(default=True)
    # together with prefix_identifier from type class the short internal identifier e.g. LZ1
    internal_identifier = models.IntegerField()

    def __str__(self) -> str:
        return self.type.name + " " + str(self.type.prefix_identifier) + str(self.internal_identifier)


class Reservation(models.Model):
    reserver = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='reserver')
    reserved_at = models.DateTimeField(auto_now_add=True)
    reserved_from = models.DateField()
    reserved_until = models.DateField()
    objecttype = models.ForeignKey(RentalObjectType, on_delete=models.CASCADE)
    operation_number = models.BigIntegerField()
    count = models.PositiveSmallIntegerField()

    def __str__(self) -> str:
        return 'reservation: ' + str(self.operation_number)


class Rental(models.Model):
    rentedobjects = models.ForeignKey(RentalObject, on_delete=models.CASCADE)
    renter = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='renter')
    lender = models.ForeignKey(User, blank=True, null=True,
                               default=None, on_delete=models.CASCADE, related_name='lender')
    return_processor = models.ForeignKey(User, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                         related_name='return_processor', verbose_name='person who processes the return')
    canceled = models.BooleanField()
    operation_number = models.BigIntegerField()
    handed_out_at = models.DateTimeField(null=True, default=None)
    received_back_at = models.DateTimeField(
        null=True, default=None, blank=True)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return 'Rental: ' + str(self.operation_number)


class OnPremiseTimeSlot(models.Model):
    day = models.SmallIntegerField()
    start_time = models.TimeField()
    duration = models.DurationField()


class OnPremiseBlockedTimes(models.Model):
    """
    To block specific days e.g. someone is ill
    """
    starttime = models.DateTimeField(default=None, null=False)
    endtime = models.DateTimeField(default=None, null=False)


class OnPremiseBooking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    showed_up = models.BooleanField()
    start_datetime = models.DateTimeField()
    duration = models.DurationField()


class Notification(models.Model):
    type = models.CharField(max_length=100, default='email')
    receiver = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    added_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    send_at = models.DateTimeField(default=timezone.now)


class Settings(models.Model):
    """
    for general dynamic Settings like general lenting day and rocketchat url and email setup
    """
    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_settings',
                fields=['type']
            )
        ]
    type = models.CharField(max_length=100)
    value = models.CharField(max_length=100)


class Suggestion(models.Model):
    """
    for suggestions which obejcts should be rented together
    """
    suggestion = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE, related_name='suggestion')
    suggestion_for = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE, related_name='suggestion_for')
