from django.contrib import admin

from .models import RentalObject, RentalObjectType, Category

# Register your models here.
admin.site.register(RentalObject)
admin.site.register(RentalObjectType)
admin.site.register(Category)
