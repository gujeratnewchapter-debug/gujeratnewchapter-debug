from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    message = 'Only administrators can manage support calls.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_super_admin)
