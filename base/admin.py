from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import RentalObject, RentalObjectType, Category,Profile, Priority, ObjectTypeInfo, Reservation, Rental, Tag, Text


# Register your models here.
admin.site.register(RentalObject)
admin.site.register(RentalObjectType)
admin.site.register(Category)
admin.site.register(Priority)
admin.site.register(ObjectTypeInfo)
admin.site.register(Profile)
admin.site.register(Permission)
admin.site.register(Reservation)
admin.site.register(Rental)
admin.site.register(Tag)
admin.site.register(Text)