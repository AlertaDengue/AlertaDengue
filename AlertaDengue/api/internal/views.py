from pydantic import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import list_notifications


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            payload = list_notifications(request.query_params)
        except ValidationError as exc:
            return Response({"detail": exc.errors()}, status=400)

        return Response(payload)
