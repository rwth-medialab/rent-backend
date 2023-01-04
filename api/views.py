import hashlib

from django.contrib.auth import login
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.mail import send_mail
from django.template import Context, Template
from django.template.loader import get_template
from django.forms.models import model_to_dict

from rest_framework import status
from rest_framework.request import Request
from rest_framework import viewsets
from rest_framework import permissions
from knox.auth import TokenAuthentication
from rest_framework.authtoken.serializers import AuthTokenSerializer
from knox.views import LoginView as KnoxLoginView

# new aproach
from rest_framework.response import Response
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes

from .serializers import ObjectTypeInfoSerializer, CategorySerializer, UserSerializer, RentalObjectSerializer, UserCreationSerializer, GroupSerializer, KnowLoginUserSerializer, RentalObjectTypeSerializer, ReservationSerializer, RentalSerializer, TagSerializer, TextSerializer
from .permissions import UserPermission, GroupPermission

from base.models import RentalObject, RentalObjectType, Category, Reservation, Rental, Profile, Tag, ObjectTypeInfo, Text
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
    def email_validation(self, request: Request):
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
        return Response(data={'success': False, 'detail': "Der Link wurde entweder schon benutzt oder der Link ist falsch, bitte stelle sicher dass der Link richtig eingegeben wurde"})
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
        use default implementation, but remove password from returned data. 
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        data = serializer.data
        data['password'] = ''
        # TODO move Template to DB
        templateString = """Hallo {{first_name}}, 
bitte aktiviere dein Konto unter {{validation_link}} """
        templateData = model_to_dict(User.objects.get(pk=data['id']))
        templateData['frontend_host'] = settings.FRONTEND_HOST
        templateData['hash'] = hashlib.sha256(
            (str(templateData["date_joined"]) + templateData["username"] + settings.EMAIL_VALIDATION_HASH_SALT).encode("utf-8")).hexdigest()
        templateData['validation_link'] = f"{templateData['frontend_host']}validate/{templateData['hash']}"
        template = Template(templateString)
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

    @action(detail=True, methods=['GET'])
    def available(self, request: Request, pk=None):
        logger.info("available")
        pass

    def get_queryset(self):
        # logger.info(self.request.META)
        # logger.info(self.request.is_secure())
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
        queryset = ObjectTypeInfo.objects.all()
        getdict = self.request.GET
        if 'public' in getdict and getdict['public'] in ['True', 'true']:
            queryset.filter(public=True)
        elif 'public' in getdict:
            queryset.filter(public=False)
        if 'object_type' in getdict:
            queryset.filter(object_type=int(getdict['type']))
        return queryset
