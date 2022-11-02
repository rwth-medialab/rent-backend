from multiprocessing import AuthenticationError
from urllib import request
from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from django.contrib.auth import login
from django.contrib.auth.models import User, Group

from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework import viewsets
from rest_framework import permissions
from knox.auth import TokenAuthentication
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView

# new aproach
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes

from .serializers import CategorySerializer, RentalObjectSerializer, UserSerializer, GroupSerializer, KnowLoginUserSerializer,RentalObjectTypeSerializer
from .permissions import UserPermission, GroupPermission

from base.models import RentalObject, RentalObjectType, Category

# Allow to Login with Basic auth for testing purposes
import logging

logger = logging.getLogger(name="django")

class LoginView(KnoxLoginView):
    permission_classes = [permissions.AllowAny, ]

    def post(self, request, format=None):
        logger.info(request.data)
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)
    def get_user_serializer_class(self):
        return KnowLoginUserSerializer

# Api Endpoint to check if credentials are valid
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def checkCredentials(request:Request):
    return(Response(status=200))

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [UserPermission]

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [GroupPermission]

class RentalobjectViewSet(viewsets.ModelViewSet):
    queryset = RentalObject.objects.all()
    serializer_class = RentalObjectSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

class RentalobjectTypeViewSet(viewsets.ModelViewSet):
    queryset = RentalObjectType.objects.all()
    serializer_class = RentalObjectTypeSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]