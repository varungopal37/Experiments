from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView
from rest_framework.response import Response

@extend_schema(
    summary="Retrieve a User's Profile by ID",
    description="Fetches detailed profile information for a given user ID.",
)
class UserProfileView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"message": "This is a documented view."})

class UserSettingsView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"message": "This is an undocumented view."})