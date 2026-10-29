"""Small API of the demo shop, built with Django REST framework."""

from rest_framework import viewsets
from rest_framework.authentication import BasicAuthentication
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


class OrderStatsAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"orders": 0})


class StatusAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


class PartnerOrderAPI(APIView):
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response([])

    def post(self, request):
        return Response(status=201)


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated & ~IsAdminUser]  # customers, not the staff

    def list(self, request):
        return Response([])

    def create(self, request):
        return Response(status=201)

    def retrieve(self, request, pk=None):
        return Response({"id": pk})

    def destroy(self, request, pk=None):
        return Response(status=204)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def refresh_cache(request):
    return Response(status=202)
