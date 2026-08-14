"""Views for the public REST API v1 surface."""

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class PublicAPIRootView(APIView):
    """Describe the available public REST API v1 surface."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Return the public API version and currently available routes."""
        return Response(
            {
                "api": "public",
                "version": "v1",
                "status": "ok",
                "routes": {},
            }
        )
