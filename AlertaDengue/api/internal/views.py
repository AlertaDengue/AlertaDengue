from api.internal.permissions import HasNotificationAPIAccess
from api.internal.services import list_notifications
from django.db import DatabaseError
from pydantic import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView


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
