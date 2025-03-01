from rest_framework import permissions

class IsManager(permissions.BasePermission):
    #Custom permission to only allow access if the user is in the 'manager' group.

    def has_permission(self, request, view):
        # Check if the user is authenticated and in the 'manager' group
        return request.user.is_authenticated and request.user.groups.filter(name="Manager").exists()