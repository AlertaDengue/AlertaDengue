from api.internal.constants import NOTIFICATION_API_GROUP_NAME
from rest_framework.permissions import BasePermission


class HasNotificationAPIAccess(BasePermission):
    message = "User does not have access to the notifications API."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        if user.is_superuser:
            return True

        return user.groups.filter(name=NOTIFICATION_API_GROUP_NAME).exists()
