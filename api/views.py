import hashlib
from datetime import datetime, timedelta
from django.contrib.auth import login
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.template.loader import get_template
from django.forms.models import model_to_dict
from django.core.exceptions import FieldError
from django.db.models import Max, Q, F
from django.utils import timezone
from django.http import HttpResponse, FileResponse

from rest_framework import status
from rest_framework.request import Request
from rest_framework import viewsets, renderers
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

from docxtpl import DocxTemplate
import io


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
        return Response(status=status.HTTP_400_BAD_REQUEST, data={'success': False, 'detail': "Der Link wurde entweder schon benutzt oder der Link ist falsch, bitte stelle sicher dass der Link richtig eingegeben wurde"})
        # {key:value for key, value in }

    def get_serializer_class(self):
        """
        use another serializer to reduce the amount of "magic"
        """
        if self.action == 'create':
            return UserCreationSerializer
        else:
            if self.request.user.has_perm("base.inventory_editing"):
                # response with all data
                return serializers.AdminUserSerializer
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
            name='signup_mail').first().content.replace(r"%}}</p>", r"%}}").replace(r"<p>{{%", r"{{%"))
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
        user_priority = request.user.profile.prio
        instance = models.RentalObjectType.max_rent_duration(
            pk=pk, prio=user_priority)

        serializer = serializers.MaxRentDurationSerializer(instance)
        return Response(serializer.data)

    @action(detail=True, url_path="freeobjects", methods=['GET'])
    def currently_free_objects(self, request: Request, pk=None):
        object_status = models.RentalObjectStatus.objects.all().filter(from_date__lte=timezone.now(), until_date__gte=timezone.now(),
                                                                       rentable=False, rental_object__in=RentalObject.objects.filter(type=pk))
        queryset = models.RentalObject.objects.filter(
            type=pk, rentable=True).exclude(rentalobjectstatus__in=object_status)
        result = []
        for rental_object in queryset:
            query_res = rental_object.rental_set.filter(
                received_back_at__isnull=True, handed_out_at__lte=timezone.now())
            if len(query_res) == 0:
                data = model_to_dict(rental_object)
                result.append(data)

        return Response(result)

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
        ret = models.RentalObjectType.available(
            pk=pk, until_date=until_date, from_date=from_date)
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

    @action(detail=False, methods=['POST'], url_path="bulk", permission_classes=[permissions.IsAuthenticated])
    def bulk_create(self, request: Request):
        data = request.data['data']
        if models.Reservation.objects.all().exists():
            operation_number = models.Reservation.objects.aggregate(
                Max('operation_number'))['operation_number__max']+1
        else:
            operation_number = 1

        response_data = []
        for reservation in data:
            if reservation['count'] > models.RentalObjectType.available(reservation['objecttype'], datetime.strptime(reservation['reserved_from'], "%Y-%m-%d").replace(tzinfo=timezone.get_current_timezone()), datetime.strptime(reservation['reserved_until'], "%Y-%m-%d").replace(tzinfo=timezone.get_current_timezone()))['available']:
                return Response({'data': 'not enough objects available'}, status=status.HTTP_400_BAD_REQUEST)
        template_data = {"reservations": []}
        for reservation in data:
            # merge reservations of the same type and not aleardy rented
            if models.Reservation.objects.filter(
                    reserved_from=reservation["reserved_from"],
                    reserved_until=reservation["reserved_until"],
                    objecttype=reservation["objecttype"],
                    reserver=request.user.profile.pk).exclude(
                        rental__in=Rental.objects.filter(rented_object__type=reservation['objecttype'])).count() == 0:
                logger.info("resre")
                reservation['operation_number'] = operation_number
                reservation['reserver'] = request.user.profile.pk
                serializer = serializers.BulkReservationSerializer(
                    data=reservation)
                serializer.is_valid(raise_exception=True)
                template_data["reservations"].append(serializer.validated_data)
                serializer.save()
            else:
                count = reservation['count']
                reservation = models.Reservation.objects.get(
                    reserved_from=reservation["reserved_from"], reserved_until=reservation["reserved_until"], objecttype=reservation["objecttype"], reserver=request.user.profile.pk)
                reservation.count += count
                reservation.save()
                serializer = serializers.BulkReservationSerializer(reservation)

            response_data.append(serializer.data)
        template_data = {**template_data,
                         "lenting_start_hour": models.Settings.objects.get(type="lenting_start_hour").value,
                         "lenting_end_hour": models.Settings.objects.get(type="lenting_end_hour").value,
                         "returning_start_hour": models.Settings.objects.get(type="returning_start_hour").value,
                         "returning_end_hour": models.Settings.objects.get(type="returning_end_hour").value, }
        logger.info(template_data)
        template = Template(models.Text.objects.filter(
            name='reservation_confirmation_mail').first().content.replace(r"%}}</p>", r"%}}").replace(r"<p>{{%", r"{{%"))
        message = template.render(Context(template_data))
        if len(template_data['reservations']) > 0:
            send_mail(subject="Deine Reservierung", message=message, html_message=message,
                      from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[template_data['reservations'][0]["reserver"].user.email])
        return Response(data={'data': response_data})

    @ action(detail=False, methods=['POST'], url_path="download_form", permission_classes=[permissions.IsAuthenticated])
    def download_form(self, request: Request):
        """
        expecting data in [{reserver: {'user': {first_name:string, last_name:string, email:string} }, objecttype: {name:string, prefix_identifier:string}, slectedObjects: [pk:int], reserved_from: %Y-%m-%d :string, reserved_until:string }] for each type an instance
        """
        context = {'rented_items': [], 'reserver': {}}
        for reservation in request.data:
            context['reserver']['last_name'] = reservation['reserver']['user']['last_name']
            context['reserver']['first_name'] = reservation['reserver']['user']['first_name']
            context['reserver']['email'] = reservation['reserver']['user']['email']
            context['rented_items'].append({'reserved_from': reservation['reserved_from'], 'reserved_until': reservation['reserved_until'], 'count': reservation['count'], 'name': reservation['objecttype']['name'], 'identifier': ",".join(
                [reservation['objecttype']['prefix_identifier'] + str(models.RentalObject.objects.get(pk=thing).internal_identifier) for thing in reservation['selectedObjects']])})
        filepath = models.Files.objects.get(name='rental_form').file.path
        doc = DocxTemplate(filepath)
        doc.render(context=context)
        file = io.BytesIO()
        doc.save(file)
        # we have to use djangos Response class here because the DRF's class does weird stuff
        return HttpResponse(file.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


class RentalViewSet(viewsets.ModelViewSet):
    queryset = Rental.objects.all()
    serializer_class = RentalSerializer
    # TODO assign rights
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = models.Rental.objects.all()
        if self.request.user.is_staff:
            queryset = queryset
        else:
            queryset = queryset.filter(reservation__reserver=self.request.user)
        if "open" in self.request.GET and self.request.GET["open"] in ["true", "True"]:
            queryset = queryset.filter(received_back_at__isnull=True)
        return queryset

    @ action(detail=False, methods=['POST'], url_path="bulk", permission_classes=[permissions.IsAuthenticated])
    def bulk_rental_creation(self, request: Request):
        """
        Takes a list of reservations and turns them into rentals
        """
        if models.Rental.objects.all().exists():
            rental_number = models.Rental.objects.aggregate(
                Max('rental_number'))['rental_number__max']+1
        else:
            rental_number = 1
        template_data = []
        ret_data = []
        for reservation in request.data:
            for index in range(reservation['count']):
                rental = {}
                rental['rented_object'] = reservation['selectedObjects'][index]
                rental['lender'] = request.user.pk
                rental['rental_number'] = rental_number
                rental['handed_out_at'] = timezone.now()
                rental['reservation'] = reservation['id']
                rental['reserved_until'] = reservation['reserved_until']
                # we need an own serializer since reservation needs to be read only on the other serializer
                serializer = serializers.RentalCreateSerializer(data=rental)
                serializer.is_valid(raise_exception=True)
                template_data.append(serializer.validated_data)
                serializer.save()
                ret_data.append(serializer.data)
        template = Template(models.Text.objects.filter(
            name='rental_confirmation_mail').first().content.replace(r"%}}</p>", r"%}}").replace(r"<p>{{%", r"{{%"))
        message = template.render(Context({'rentals': template_data}))
        send_mail(subject="Dein Ausleihvorgang", message=message, html_message=message,
                  from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[template_data[0]['reservation'].reserver.user.email])
        return Response(ret_data)

    @ action(detail=False, methods=['POST'], url_path="return", permission_classes=[permissions.IsAuthenticated])
    def bulk_return(self, request: Request):
        """
        takes a list of rental ids and ends their rental duration to now.
        @return either return 400 if it does not find some rentals. otherwise returns number of changed objects
        """
        queryset = models.Rental.objects.filter(
            pk__in=request.data, received_back_at=None)
        if len(queryset) != len(request.data):
            return Response("couldn't find some of those rentals", status=status.HTTP_400_BAD_REQUEST)
        updated = queryset.update(
            reserved_until= timezone.now().date(), received_back_at=timezone.now())
        return Response(updated)


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

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'name' in self.request.GET:
            queryset = queryset.filter(name=self.request.GET['name'])
        return queryset


class MaxRentDurationViewSet(viewsets.ModelViewSet):
    queryset = models.MaxRentDuration.objects.all()
    serializer_class = serializers.MaxRentDurationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        getdict = self.request.GET
        if 'object_type' in getdict:
            queryset = queryset.filter(
                rental_object_type=getdict['object_type'])
        return queryset


class PassthroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = ''
    format = ''

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class FilesViewSet(viewsets.ModelViewSet):
    queryset = models.Files.objects.all()
    serializer_class = serializers.FilesSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if 'name' in self.request.GET:
            queryset.filter(name=self.request.GET['name'])
        return queryset

    @ action(detail=False, methods=['POST'], url_path="rental_form_template", permission_classes=[permissions.IsAdminUser])
    def update_rental_form_set(self, request: Request):
        data = request.data
        instance = models.Files.objects.get(name='rental_form')
        instance.file = data['file']
        data = serializers.FilesSerializer(
            instance=instance).is_valid(raise_exception=True).save()
        return Response(data=data)

    @ action(detail=False, methods=['GET'], url_path="download", permission_classes=[permissions.IsAdminUser])
    def download(self, request: Request):
        if ('name' not in request.GET):
            return HttpResponse("missing 'name' query param", status.HTTP_400_BAD_REQUEST)
        instance = self.queryset.filter(name=request.GET['name']).first()
        file = instance.file.open()
        return HttpResponse(file, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
