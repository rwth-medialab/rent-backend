from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from datetime import datetime
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
    extension of User model for addtitional information. since we check those permissions through here we create them here. (Automatically created through the meta tag)
    """
    class Meta:
        permissions = [
            ("inventory_editing",
             "able to edit and create the inventory and got nearly full access"),
            ("lending_access", "is able to lend stuff")
        ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, blank=True, related_name="profile")
    # Since people are already somewhat authenticated through their email allow them to lend even without validation.On authorization validation a corresponding Prio field must be set
    prio = models.ForeignKey(
        Priority, on_delete=models.SET_NULL, null=True, blank=True, default=Priority.objects.get(prio=99))
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


class RentalObjectStatus(models.Model):
    """
    A Status to prevent a Rentalobject to be rent. for example planned maintenance. defaults to now until infinity.
    """
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(from_date__lte=models.F('until_date')),
                name="object_status_enforce_from_date_lte_until_date"
            )
        ]
    rental_object = models.ForeignKey(
        RentalObject, verbose_name="Rentalobject", on_delete=models.CASCADE)
    reason = models.TextField(default="defekt")
    from_date = models.DateField(default=timezone.now)
    until_date = models.DateField(default=datetime.max)
    rentable = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.rental_object.__str__()) + " status"


class Reservation(models.Model):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(reserved_from__lte=models.F('reserved_until')),
                name="reservation_reserved_from_date_lte_reserved_until"
            )
        ]
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
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    handed_out_at__lte=models.F('received_back_at')),
                name="rental_handed_out_lte_received_date"
            )
        ]
    rented_object = models.ForeignKey(RentalObject, on_delete=models.CASCADE)
    renter = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name='renter')
    lender = models.ForeignKey(User, blank=True, null=True,
                               default=None, on_delete=models.CASCADE, related_name='lender')
    return_processor = models.ForeignKey(User, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                         related_name='return_processor', verbose_name='person who processes the return')
    canceled = models.DateTimeField(null=True, blank=True, default=None)
    operation_number = models.BigIntegerField()
    handed_out_at = models.DateTimeField(default=timezone.now)
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
    """
    for planned notificaitons
    """
    type = models.CharField(max_length=100, default='email')
    receiver = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField()
    added_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True)
    send_at = models.DateTimeField(default=timezone.now)


class Settings(models.Model):
    """
    for general dynamic Settings like general lenting day and rocketchat url
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
    public = models.BooleanField()

    def __str__(self) -> str:
        return self.type


class Text(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField(default="", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='Unique_text_slug',
                fields=['name']
            )
        ]
        verbose_name = ("Text")
        verbose_name_plural = ("texts")

    def __str__(self):
        return self.name


class Suggestion(models.Model):
    """
    for suggestions which objects should be rented together
    """
    suggestion = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE, related_name='suggestion')
    suggestion_for = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE, related_name='suggestion_for')


class MaxRentDuration(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_prio_type',
                fields=['prio', 'rental_object_type']
            )
        ]
    prio = models.ForeignKey(Priority, on_delete=models.CASCADE)
    rental_object_type = models.ForeignKey(
        RentalObjectType, on_delete=models.CASCADE)
    duration = models.DurationField()
