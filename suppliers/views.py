"""API views for suppliers and supplier catalog management."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.enums import ViewAction
from config.permissions import IsAdminOrReadOnly, IsAdminUser
from suppliers.filters import SupplierCarFilter, SupplierDiscountFilter, SupplierFilter
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from suppliers.serializers import (
    SupplierCarListSerializer,
    SupplierCarSerializer,
    SupplierDiscountSerializer,
    SupplierListSerializer,
    SupplierSerializer,
    SupplierStatisticsSerializer,
)
from suppliers.services import SupplierCarService, SupplierService


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SupplierFilter
    search_fields = ["name", "email", "description"]
    ordering_fields = ["name", "rating", "total_sales", "total_revenue", "founded_year", "created_at"]
    ordering = ["-rating", "name"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return SupplierListSerializer
        return SupplierSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return SupplierService.get_all_active_suppliers()
        return Supplier.objects.all()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=True, methods=["get"])
    def cars(self, request, pk=None):
        supplier = self.get_object()
        cars = SupplierCarService.get_supplier_cars_by_supplier(supplier.id)
        serializer = SupplierCarListSerializer(cars, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        supplier = self.get_object()
        stats = SupplierService.get_supplier_statistics(supplier)
        serializer = SupplierStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        instance = self.get_object()
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class SupplierCarViewSet(viewsets.ModelViewSet):
    queryset = SupplierCar.objects.select_related("supplier", "car_model").all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SupplierCarFilter
    search_fields = ["supplier__name", "car_model__brand", "car_model__model"]
    ordering_fields = ["price", "available_quantity", "delivery_days", "times_sold", "created_at"]
    ordering = ["price"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return SupplierCarListSerializer
        return SupplierCarSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return SupplierCarService.get_all_active_supplier_cars()
        return SupplierCar.objects.select_related("supplier", "car_model").all()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["get"])
    def best_prices(self, request) -> Response:
        cars = SupplierCarService.get_best_prices()
        serializer = self.get_serializer(cars, many=True)
        return Response(serializer.data)


class SupplierDiscountViewSet(viewsets.ModelViewSet):
    queryset = SupplierDiscount.objects.select_related("supplier", "dealership").all()
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = SupplierDiscountFilter
    ordering_fields = ["discount_percent", "min_purchases", "created_at"]
    ordering = ["-discount_percent"]

    serializer_class = SupplierDiscountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def perform_destroy(self, instance):
        instance.soft_delete()
