from django.urls import include,path
from . import views
from rest_framework import routers
from knox import views as knox_views
from api.views import LoginView

router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)

urlpatterns = [
    path(r'rentalobjects', views.getRentalObjects),
    path(r'auth/login/', LoginView.as_view(), name='knox_login'),
    path(r'auth/logout/', knox_views.LogoutView.as_view(), name='knox_logout'),
    path(r'auth/logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
    ]
urlpatterns += router.urls