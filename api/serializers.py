from dataclasses import fields
from django.contrib.auth.models import User, Group
from rest_framework import serializers
import logging
from base.models import RentalObject

logger = logging.getLogger(name='django')

class PrivateField(serializers.ReadOnlyField):
    def get_attribute(self, instance):
        if self.context['request'].user.has_perm('a'):
            return super(PrivateField,self).get_attribute(instance)
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

    #def update(self, instance, validated_data):
    #    logger.info(validated_data)
    #    return super().update(instance, validated_data)



class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']

class RentalObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = RentalObject
        fields = '__all__'