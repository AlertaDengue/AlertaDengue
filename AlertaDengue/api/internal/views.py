from django.db import DatabaseError
from pydantic import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasNotificationAPIAccess
from .services import list_notifications


class NotificationListView(APIView):
    permission_classes = [HasNotificationAPIAccess]

    def get(self, request):
        try:
            payload = list_notifications(request.query_params)
        except ValidationError as exc:
            return Response({"detail": exc.errors()}, status=400)
        except DatabaseError:
            return Response(
                {"detail": "Database error while listing notifications."},
                status=500,
            )

        return Response(payload)
