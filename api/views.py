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
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView

# new aproach
from rest_framework.response import Response
from rest_framework.decorators import api_view, action

from .serializers import RentalObjectSerializer, UserSerializer, GroupSerializer

from base.models import RentalObject

# Allow to Login with Basic auth for testing purposes
import logging

logger = logging.getLogger(name="django")

class LoginView(KnoxLoginView):
    permission_classes = [permissions.AllowAny, ]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)


def index(request):
    return HttpResponse("Hello, world. You're at index.")

@api_view(['GET'])
def getRentalObjects(request):
    queryset = RentalObject.objects.all()
    serializer = RentalObjectSerializer(queryset, many=True)
    return Response(serializer.data)

@action(detail=True ,methods=["PATCH", "GET", "POST"])
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited. 
    """
    queryset = User.objects.all().order_by('-date_joined')
    logger.info(queryset)
    serializer_class = UserSerializer
    #permission_classes = [permissions.IsAuthenticated]
    def update(self, request:Request, *args, **kwargs):
        logger.info(super())
        return super().update(request,pk=None)
    def partial_update(self, request, *args, **kwargs):
        logger.info(request.data)
        return super().partial_update(request,pk=None)

class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]
