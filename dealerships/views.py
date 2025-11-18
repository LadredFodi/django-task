"""API views for dealerships, inventory, and purchases."""

from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.enums import ViewAction
from config.permissions import IsAdminOrReadOnly, IsAdminUser
from dealerships.filters import DealershipFilter, DealershipInventoryFilter, DealershipPreferenceFilter, PurchaseFilter
from dealerships.models import Dealership, DealershipInventory, DealershipPreference, Purchase
from dealerships.serializers import (
    DealershipInventoryListSerializer,
    DealershipInventorySerializer,
    DealershipListSerializer,
    DealershipPreferenceSerializer,
    DealershipSerializer,
    DealershipStatisticsSerializer,
    PurchaseListSerializer,
    PurchaseSerializer,
    PurchaseStatisticsSerializer,
)
from dealerships.services import DealershipInventoryService, DealershipService, PurchaseService


class DealershipViewSet(viewsets.ModelViewSet):

    queryset = Dealership.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DealershipFilter
    search_fields = ["name", "city", "address", "email", "description"]
    ordering_fields = ["name", "city", "total_sales", "total_revenue", "total_profit", "balance", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return DealershipListSerializer
        return DealershipSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return DealershipService.get_all_active_dealerships()
        return Dealership.objects.all()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=["get"])
    def inventory(self, request, pk=None):
        dealership = self.get_object()
        inventory = DealershipInventoryService.get_inventory_by_dealership(dealership.id)
        serializer = DealershipInventoryListSerializer(inventory, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def purchases(self, request, pk=None):
        dealership = self.get_object()
        purchases = PurchaseService.get_purchases_by_dealership(dealership.id)
        serializer = PurchaseListSerializer(purchases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        dealership = self.get_object()
        stats = DealershipService.get_dealership_statistics(dealership)
        serializer = DealershipStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def nearby(self, request):
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        radius = request.query_params.get("radius", 50)

        if not lat or not lon:
            return Response({"error": "Lat and lon parameters are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lat = float(lat)
            lon = float(lon)
            radius = float(radius)
        except ValueError:
            return Response({"error": "Invalid coordinates or radius value"}, status=status.HTTP_400_BAD_REQUEST)

        queryset = DealershipService.find_nearby(lat, lon, radius)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def update_balance(self, request, pk=None):
        dealership = self.get_object()
        amount = request.data.get("amount")

        if not amount:
            return Response({"error": "Amount parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({"error": "Invalid amount value"}, status=status.HTTP_400_BAD_REQUEST)

        updated = DealershipService.update_balance(dealership, amount)
        serializer = self.get_serializer(updated)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):

        instance = self.get_object()
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class DealershipPreferenceViewSet(viewsets.ModelViewSet):

    queryset = DealershipPreference.objects.select_related("dealership").all()
    serializer_class = DealershipPreferenceSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = DealershipPreferenceFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_destroy(self, instance):
        instance.soft_delete()


class DealershipInventoryViewSet(viewsets.ModelViewSet):

    queryset = DealershipInventory.objects.select_related("dealership", "car_model").all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DealershipInventoryFilter
    search_fields = ["dealership__name", "car_model__brand", "car_model__model"]
    ordering_fields = ["quantity", "selling_price", "times_sold", "last_sale_date", "created_at"]
    ordering = ["-quantity"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return DealershipInventoryListSerializer
        return DealershipInventorySerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return DealershipInventoryService.get_all_active_inventory()
        return DealershipInventory.objects.select_related("dealership", "car_model").all()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["get"])
    def available(self, request):
        available = DealershipInventoryService.get_available_inventory()
        serializer = self.get_serializer(available, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def popular(self, request):
        popular = DealershipInventoryService.get_popular_inventory(limit=20)
        serializer = self.get_serializer(popular, many=True)
        return Response(serializer.data)


class PurchaseViewSet(viewsets.ModelViewSet):

    queryset = Purchase.objects.select_related("dealership", "supplier", "car_model").all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PurchaseFilter
    search_fields = ["dealership__name", "supplier__name", "car_model__brand", "car_model__model"]
    ordering_fields = ["quantity", "total_price", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return PurchaseListSerializer
        return PurchaseSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        stats = PurchaseService.get_statistics()
        serializer = PurchaseStatisticsSerializer(stats)
        return Response(serializer.data)
