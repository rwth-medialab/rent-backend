from multiprocessing import AuthenticationError
from urllib import request
from django.shortcuts import render
import json

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
from rest_framework.renderers import JSONRenderer

# new aproach
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes

from .serializers import ObjectTypeInfoSerializer, CategorySerializer, RentalObjectSerializer, UserSerializer, GroupSerializer, KnowLoginUserSerializer, RentalObjectTypeSerializer, ReservationSerializer, RentalSerializer, TagSerializer
from .permissions import UserPermission, GroupPermission

from base.models import RentalObject, RentalObjectType, Category, Reservation, Rental, Profile, Tag, ObjectTypeInfo

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
def checkCredentials(request: Request):
    return (Response(status=200))


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [UserPermission]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def create_user(self, request: Request):
        postDict = request.data
        logger.info(postDict)
        user = User.objects.create_user(username=postDict['username'], email=postDict['email'],
                                        first_name=postDict['firstname'], last_name=postDict['lastname'], password=postDict['password'])
        Profile.objects.create(user=user)
        return Response({'created': 'successfull'}, status=200)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [GroupPermission]


class RentalobjectViewSet(viewsets.ModelViewSet):
    queryset = RentalObject.objects.all().order_by('internal_identifier')
    serializer_class = RentalObjectSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = RentalObject.objects.all()
        getdict = self.request.GET
        if 'type' in getdict:
            queryset = queryset.filter(type=getdict['type'])

        return queryset


class RentalobjectTypeViewSet(viewsets.ModelViewSet):
    queryset = RentalObjectType.objects.all()
    serializer_class = RentalObjectTypeSerializer
    # TODO assign rights
    # TODO Allow list all
    # TODO Allow retrieve all
    # TODO Allow update/partial inventory rights
    permission_classes = [permissions.AllowAny]
    @action(detail=True,methods=['GET'])
    def available(self, request:Request ,pk=None):
        logger.info("available")
        pass

    def get_queryset(self):
        #logger.info(self.request.META)
        #logger.info(self.request.is_secure())
        queryset = RentalObjectType.objects.all().order_by('category','name')
        getdict = self.request.GET
        if 'visible' in getdict and getdict['visible'] in ['true', 'True']:
            queryset = queryset.filter(visible = True)
        return queryset


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]


class ReservationViewSet(viewsets.ModelViewSet):
    """
    Limit returned objects by open, from and until get requests
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Reservation.objects.all()
        getdict = self.request.GET
        if 'from' in getdict:
            queryset = queryset.filter(reserved_from__gte=getdict['from'])
        if 'until' in getdict:
            queryset = queryset.filter(reserved_from__lte=getdict['until'])
        if 'open' in getdict:
            if getdict['open'] in ['true', 'True']:
                # remove all reservations that already got a corresponding rental
                queryset = queryset.exclude(rental__in=Rental.objects.all())
        if 'unique' in getdict:
            if getdict['unique'] in ['true', 'True']:
                queryset = queryset.distinct('operation_number')
        if 'operation_number' in getdict:
            queryset = queryset.filter(
                operation_number=getdict['operation_number'])
        return queryset


class RentalViewSet(viewsets.ModelViewSet):
    queryset = Rental.objects.all()
    serializer_class = RentalSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    # TODO assign rights everyone list, retrieve, post patch and put only with permission and logged in
    permission_classes = [permissions.AllowAny]

class ObjectTypeInfoViewSet(viewsets.ModelViewSet):
    # TODO Permission that limits access to non Public objects
    queryset = ObjectTypeInfo.objects.all()
    serializer_class = ObjectTypeInfoSerializer

    def get_queryset(self):
        # get default queryset, now limit it...
        queryset = ObjectTypeInfo.objects.all()
        getdict = self.request.GET
        if 'public' in getdict and getdict['public'] in ['True', 'true']:
            queryset.filter(public=True)
        elif 'public' in getdict:
            queryset.filter(public=False)
        if 'object_type' in getdict:
            queryset.filter(object_type=int(getdict['type']))
        return queryset
