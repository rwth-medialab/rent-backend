from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import RentalObject, RentalObjectType, Category,Profile, Priority, PublicInfoObjectType, InternalInfoObjectType



# Register your models here.
admin.site.register(RentalObject)
admin.site.register(RentalObjectType)
admin.site.register(Category)
admin.site.register(Priority)
admin.site.register(PublicInfoObjectType)
admin.site.register(InternalInfoObjectType)
admin.site.register(Profile)
admin.site.register(Permission)