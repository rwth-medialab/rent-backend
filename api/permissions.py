from rest_framework import permissions
from django.http import HttpRequest

class UserPermission(permissions.BasePermission):
    def has_permission(self, request:HttpRequest, view):
        if view.action == 'list':
            return request.user.is_authenticated and request.user.is_superuser
        elif view.action == 'create':
            return True
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request:HttpRequest, view, obj):
        # Deny actions on objects if the user is not authenticated
        if not request.user.is_authenticated:
            return False

        if view.action == 'retrieve':
            return obj == request.user or request.user.is_superuser
        elif view.action in ['destroy', 'update', 'partial_update', 'list']:
            return request.user.is_superuser
        else:
            return False

class GroupPermission(permissions.BasePermission):
    def has_permission(self, request:HttpRequest, view):
        if view.action == 'list':
            return request.user.is_authenticated and request.user.is_superuser
        elif view.action == 'create':
            return request.user.is_authenticated and request.user.is_superuser
        elif view.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return True
        else:
            return False

    def has_object_permission(self, request:HttpRequest, view, obj):
        # Deny actions on objects if the user is not authenticated
        if not request.user.is_authenticated:
            return False

        if view.action == 'retrieve':
            return request.user.is_superuser
        elif view.action in ['destroy', 'update', 'partial_update', 'list']:
            return request.user.is_superuser
        else:
            return False