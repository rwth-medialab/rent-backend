from django.contrib.auth.models import User, Group
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from django.db import transaction
import logging
import re
from base.models import Category, RentalObject, RentalObjectType, Reservation, Rental, Tag, ObjectTypeInfo, Text, Profile

logger = logging.getLogger(name="django")
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model= Profile
        fields='__all__'

class UserCreationSerializer(serializers.HyperlinkedModelSerializer):
    """
    Used for user registration 
    """
    profile= ProfileSerializer(required=False)
    #password = PrivateField()
    class Meta:
        model = User
        #fields = '__all__'
        fields = ['url', 'username', 'password', 'email',
                  'groups', 'id', 'first_name', 'last_name', 'profile']

    def validate_email(self, email):
        """
        overwrite the email validation to prevent multiuse of emails.
        """
        #TODO regular expression to db raw string is the same as in js 
        regex = re.compile('\\S+@([a-zA-Z0-9]+\\.)?rwth-aachen\\.de')
        result = regex.fullmatch(email)
        if not (result and result.group(0)==email): 
            raise serializers.ValidationError("Email ist im falsche Format")
        if User.objects.all().filter(email=email).count()>0:
            raise serializers.ValidationError("Email bereits in Benutzung")
        return email

    @transaction.atomic
    def create(self, validated_data):
        """
        creates the user object in db and disables the login
        """
        validated_data['is_active'] = False
        if 'groups' in validated_data:
            del validated_data['groups']
        profile_data = validated_data.pop('profile')
        user = User.objects.create_user(**validated_data)
        profile_data['user'] = user.id
        profile_serializer = ProfileSerializer(data=profile_data)
        profile_serializer.is_valid(raise_exception=True)
        profile_serializer.save()
        logger.info(profile_data)
        #Profile.objects.create(**profile_serializer.data)
        return user



class UserSerializer(serializers.HyperlinkedModelSerializer):
    profile= ProfileSerializer()

    #password = PrivateField()
    class Meta:
        model = User
        #fields = '__all__'
        fields = ['url', 'username', 'email',
                  'groups', 'id', 'first_name', 'last_name', 'profile']

    def create(self, validated_data):
        profile_data = validated_data.pop('profile')
        user = User.objects.create(**validated_data)
        Profile.objects.create(user=user, **profile_data)
        return user

    def update(self, instance:User, validated_data:dict):
        logger.info(type( instance))
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.save()
        # Profile is not neccessarily needed to update User
        try:
            profile_data = validated_data.pop('profile')
            profile = instance.profile
        except Profile.DoesNotExist:
            return instance
        except KeyError:
            return instance

        ProfileSerializer.update(profile, profile, profile_data)

        return instance

class KnowLoginUserSerializer(serializers.ModelSerializer):
    user_permissions = serializers.SerializerMethodField(
        'get_user_permissions_name')

    class Meta:
        model = User
        fields = ['username', 'email', 'groups',
                  'is_staff', 'is_superuser', 'user_permissions']

    def get_user_permissions_name(self, obj):
        # replace ids with Permission names to reduce the number of requests
        return obj.get_all_permissions()


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class RentalObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalObject
        fields = '__all__'


class RentalObjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalObjectType
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('name', 'description', 'id')


class ReservationSerializer(serializers.ModelSerializer):
    # TODO maybe switch to slugfield
    reserverusername = serializers.SerializerMethodField(
        'get_reserverusername')
    reservername = serializers.SerializerMethodField(
        'get_reservername')
    reserverlastname = serializers.SerializerMethodField(
        'get_reserverlastname')

    class Meta:
        model = Reservation
        fields = ['count', 'id', 'objecttype', 'operation_number', 'reserved_at', 'reserved_from',
                  'reserved_until', 'reserverusername', 'reservername', 'reserverlastname']

    def get_reserverusername(self, obj: Reservation):
        # replace ids with Permission names to reduce the number of requests
        return obj.reserver.user.username

    def get_reservername(self, obj: Reservation):
        # replace ids with Permission names to reduce the number of requests
        return obj.reserver.user.first_name

    def get_reserverlastname(self, obj: Reservation):
        # replace ids with Permission names to reduce the number of requests
        return obj.reserver.user.last_name


class RentalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rental
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class ObjectTypeInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjectTypeInfo
        fields = '__all__'


class TextSerializer(serializers.ModelSerializer):
    class Meta:
        model = Text
        fields = '__all__'
