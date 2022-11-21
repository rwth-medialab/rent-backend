from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import RentalObject, RentalObjectType, Category,Profile, Priority, PublicInfoObjectType, InternalInfoObjectType, Reservation, Rental, Tag


# Register your models here.
admin.site.register(RentalObject)
admin.site.register(RentalObjectType)
admin.site.register(Category)
admin.site.register(Priority)
admin.site.register(PublicInfoObjectType)
admin.site.register(InternalInfoObjectType)
admin.site.register(Profile)
admin.site.register(Permission)
admin.site.register(Reservation)
admin.site.register(Rental)
admin.site.register(Tag)