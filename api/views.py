import hashlib
from datetime import datetime, timedelta
from datetimerange import DateTimeRange

from django.contrib.auth import login
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.template.loader import get_template
from django.forms.models import model_to_dict
from django.core.exceptions import FieldError
from django.db.models import Max
from django.utils import timezone

from rest_framework import status
from rest_framework.request import Request
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes

from knox.views import LoginView as KnoxLoginView
from knox.auth import TokenAuthentication

from .serializers import ObjectTypeInfoSerializer, CategorySerializer, UserSerializer, RentalObjectSerializer, UserCreationSerializer, GroupSerializer, KnowLoginUserSerializer, RentalObjectTypeSerializer, ReservationSerializer, RentalSerializer, TagSerializer, TextSerializer
from .permissions import UserPermission, GroupPermission
from api import serializers

from base.models import RentalObject, RentalObjectType, Category, Reservation, Rental, Profile, Tag, ObjectTypeInfo, Text
from base import models
# Allow to Login with Basic auth for testing purposes
import logging

logger = logging.getLogger(name="django")


class LoginView(KnoxLoginView):
    """
    Loginview returns a Authtoken for the user to login
    """
    permission_classes = [permissions.AllowAny, ]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginView, self).post(request, format=None)

    def get_user_serializer_class(self):
        return KnowLoginUserSerializer


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def checkCredentials(request: Request):
    """
    Api Endpoint to check if credentials are valid
    """
    return (Response(status=200))


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [UserPermission]

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def email_validation(self, request: Request):
        """
        Endpoint to validate the register email against. validates the registered hash
        """
        hash = request.POST['hash']
        # to be able to deactivate accounts last login is checked
        for model in User.objects.all().filter(is_active=False, last_login__isnull=True):
            model_hash = hashlib.sha256(
                (str(model.date_joined) + model.username + settings.EMAIL_VALIDATION_HASH_SALT).encode("utf-8")).hexdigest()
            if model_hash == hash:
                model.is_active = True
                model.save()
                # User.objects.get(pk=model.id).update(is_active=True)
                return Response(data={'success': True, 'detail': "Die Email wurde erfolgreich validiert und man kann sich mit dem verbundenen Account einloggen."})
        logger.info(hash)
        return Response(status=status.HTTP_400_BAD_REQUEST, data={'success': False, 'detail': "Der Link wurde entweder schon benutzt oder der Link ist falsch, bitte stelle sicher dass der Link richtig eingegeben wurde"})
        # {key:value for key, value in }

    def get_serializer_class(self):
        """
        use another serializer to reduce the amount of "magic"
        """
        if self.action == 'create':
            return UserCreationSerializer
        else:
            return UserSerializer

    def create(self, request, *args, **kwargs):
        """
        use default implementation, but remove password from returned data and send email to user. 
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        data = serializer.data
        data['password'] = ''
        templateData = model_to_dict(User.objects.get(pk=data['id']))
        templateData['frontend_host'] = settings.FRONTEND_HOST
        templateData['hash'] = hashlib.sha256(
            (str(templateData["date_joined"]) + templateData["username"] + settings.EMAIL_VALIDATION_HASH_SALT).encode("utf-8")).hexdigest()
        templateData['validation_link'] = f"{templateData['frontend_host']}validate/{templateData['hash']}"
        template = Template(models.Text.objects.filter(
            name='signup_mail').first().content)
        message = template.render(Context(templateData))

        # TODO validate if mail has been send
        send_mail(subject="Registrierung", message=message,
                  from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[templateData['email']])
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


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

    @action(detail=True, url_path="duration", methods=['GET'], permission_classes=[permissions.IsAuthenticated])
    def max_duration(self, request: Request, pk=None):
        """
        returns the max Duration for a user 
        """
        object_type = models.RentalObjectType.objects.get(id=pk)
        user_priority = request.user.profile.prio
        if models.MaxRentDuration.objects.filter(
                prio=user_priority, rental_object_type=object_type).exists():
            instance = models.MaxRentDuration.objects.get(
                prio=user_priority, rental_object_type=object_type)
        elif models.MaxRentDuration.objects.filter(
                rental_object_type=object_type, prio__prio__gte=user_priority.prio).order_by('prio__prio').exists():
            # fallback to default duration
            instance = models.MaxRentDuration.objects.filter(
                rental_object_type=object_type, prio__prio__gt=user_priority.prio).order_by('prio__prio').first()
        else:
            # fallback fallback to 1 week
            instance = {
                'prio': None, 'rental_object_type': object_type, 'duration': timedelta(weeks=1)}
        serializer = serializers.MaxRentDurationSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, url_path="available", methods=['GET'], permission_classes=[permissions.IsAuthenticated])
    def available_object(self, request: Request, pk=None):
        """
        takes two arguments a start date and an end date end calculates if that object is available around that time
        """
        if not models.RentalObjectType.objects.all().filter(id=pk).exists():
            raise models.RentalObjectType.DoesNotExist
        if not 'from_date' in request.query_params:
            raise FieldError("from_date query param is missing")
        if not 'until_date' in request.query_params:
            raise FieldError("until_data query param is missing")

        from_date = datetime.strptime(
            request.query_params['from_date'], "%Y-%m-%d").replace(tzinfo=timezone.get_current_timezone())
        until_date = datetime.strptime(
            request.query_params['until_date'], "%Y-%m-%d").replace(tzinfo=timezone.get_current_timezone())
        delta = until_date - from_date
        offset = settings.DEFAULT_OFFSET_BETWEEN_RENTALS
        # get all "defect" status for this type
        object_status = models.RentalObjectStatus.objects.all().filter(from_date__lte=until_date, until_date__gte=from_date,
                                                                       rentable=False, rental_object__in=models.RentalObject.objects.filter(type=pk))
        # remove all objects with an status from objects
        objects = models.RentalObject.objects.all().filter(
            type=pk).exclude(rentable=False).exclude(rentalobjectstatus__in=object_status)
        # since timedelta reduces everything to days and below we can just take the days
        # calculate timerange with most
        # logger.info(pk)
        # for reservation in list(models.Reservation.objects.filter(objecttype_id=pk)):
        #     logger.info(model_to_dict(reservation))
        #     logger.info(until_date.date())
        reservations = models.Reservation.objects.filter(
            objecttype_id=pk, reserved_from__lte=until_date.date(), reserved_until__gte=from_date.date())
        rentals = models.Rental.objects.filter(
            rented_object__in=objects, handed_out_at__lte=until_date, reservation__reserved_until__gte=from_date.date())

        count = len(objects)

        # give reservations + rentals them common keys for the dates
        normalized_list = [{**model_to_dict(x), 'from_date': x.handed_out_at.date(
        ), 'until_date': x.reservation.reserved_until} for x in rentals]
        # normalized_list = [ for x in reservations]
        for reservation in reservations:
            for _ in range(reservation.count):
                normalized_list.append(
                    {**model_to_dict(reservation), 'from_date': reservation.reserved_from, 'until_date': reservation.reserved_until})
        ret = {}
        max_value = 0
        for day_diff in range(delta.days+1):
            current_date = (from_date + timedelta(days=day_diff)).date()
            temp_value = 0
            for blocked_timerange in normalized_list:
                # calculate offset
                until_date_with_offset = (
                    blocked_timerange['until_date']+offset)
                if until_date_with_offset.isoweekday() != settings.DEFAULT_LENTING_DAY_OF_WEEK:
                    # since weekday is not a Lenting day we extend the "occupied/lended" state until the next lenting day
                    offset += timedelta(days=7-abs(
                        until_date_with_offset.isoweekday()-settings.DEFAULT_LENTING_DAY_OF_WEEK))
                if blocked_timerange['from_date'] <= current_date < blocked_timerange['until_date'] + offset:
                    temp_value += 1
            max_value = temp_value if temp_value > max_value else max_value
            ret[str(current_date)] = count-temp_value
        ret['available'] = count-max_value

        # substract objecttype reservation count could go below zero if the type has two reservations in the requested areas
        # Therefore we should only substract the reservations with the most reserved objects
        #object_reservation_max_count = models.Reservation.objects.filter(objecttype=pk ,reserved_from__lte=until_date, reserved_until__gte=from_date).aggregate(Max('count'))
        #ret['available']['count']-= object_reservation_max_count['count__max'] if object_reservation_max_count['count__max'] else 0
        return Response(data=ret)

    @action(detail=False, url_path="available", methods=['GET'], permission_classes=[permissions.IsAuthenticated])
    def available_objects(self, request: Request):
        """
        this function does the same as available_object only for querysets returns all objects available around that time
        """
        # TODO allow the supply of a specific set of types
        queryset = self.get_queryset().filter(visible=True)
        data = {}
        for object_type in queryset:
            data[object_type.id] = self.available_object(
                request=request, pk=object_type.id).data

        return Response(data)

    def get_queryset(self):
        queryset = RentalObjectType.objects.all().order_by('category', 'name')
        getdict = self.request.GET
        if 'visible' in getdict and getdict['visible'] in ['true', 'True']:
            queryset = queryset.filter(visible=True)
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


class TextViewSet(viewsets.ModelViewSet):
    queryset = Text.objects.all()
    serializer_class = TextSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Text.objects.all()
        getdict = self.request.GET
        if 'names' in getdict:
            queryset = queryset.filter(name__in=getdict['names'].split(","))
        return queryset


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
        queryset = super().get_queryset()
        getdict = self.request.GET
        if 'public' in getdict and getdict['public'] in ['True', 'true']:
            queryset.filter(public=True)
        elif 'public' in getdict:
            queryset.filter(public=False)
        if 'object_type' in getdict:
            queryset.filter(object_type=int(getdict['object_type']))
        return queryset


class PriorityViewSet(viewsets.ModelViewSet):
    queryset = models.Priority.objects.all()
    serializer_class = serializers.PrioritySerializer


class SettingsViewSet(viewsets.ModelViewSet):
    queryset = models.Settings.objects.filter(public=True)
    serializer_class = serializers.SettingsSerializer


class RentalViewSet(viewsets.ModelViewSet):
    queryset = models.Rental.objects.all()
    serializer_class = serializers.RentalSerializer

class MaxRentDurationViewSet(viewsets.ModelViewSet):
    queryset = models.MaxRentDuration.objects.all()
    serializer_class = serializers.MaxRentDurationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        getdict  = self.request.GET
        if 'object_type' in getdict:
            queryset = queryset.filter(rental_object_type=getdict['object_type'])
        return queryset