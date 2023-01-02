from dataclasses import fields
from django.contrib.auth.models import User, Group
from rest_framework import serializers
import logging
from base.models import Category, RentalObject, RentalObjectType, Reservation, Rental, Tag, ObjectTypeInfo

logger = logging.getLogger(name="django")


class PrivateField(serializers.ReadOnlyField):
    def get_attribute(self, instance):
        if self.context['request'].user.has_perm('a'):
            return super(PrivateField, self).get_attribute(instance)
        return None


class PrivateEditField(serializers.Field):
    def to_internal_value(self, data):
        data = "nils@nils.de"


class UserSerializer(serializers.HyperlinkedModelSerializer):
    #password = PrivateField()
    class Meta:
        model = User
        #fields = '__all__'
        fields = ['url', 'username', 'email', 'groups', 'password']

    # def update(self, instance, validated_data):
    #    logger.info(validated_data)
    #    return super().update(instance, validated_data)


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
    #TODO maybe switch to slugfield    
    reserverusername = serializers.SerializerMethodField(
        'get_reserverusername')    
    reservername = serializers.SerializerMethodField(
        'get_reservername')    
    reserverlastname = serializers.SerializerMethodField(
        'get_reserverlastname')
    class Meta:
        model = Reservation
        fields = ['count','id','objecttype','operation_number','reserved_at','reserved_from','reserved_until','reserverusername','reservername', 'reserverlastname']
    def get_reserverusername(self, obj:Reservation):
        # replace ids with Permission names to reduce the number of requests
        return obj.reserver.user.username
    def get_reservername(self, obj:Reservation):
        # replace ids with Permission names to reduce the number of requests
        return obj.reserver.user.first_name
    def get_reserverlastname(self, obj:Reservation):
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