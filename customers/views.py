from decimal import Decimal

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from config.enums import ViewAction
from config.permissions import IsAdminUser, IsOwnerOrAdmin
from customers.filters import CustomerFilter, SaleFilter
from customers.models import Customer, Sale
from customers.serializers import (
    CustomerListSerializer,
    CustomerRegistrationSerializer,
    CustomerSerializer,
    CustomerStatisticsSerializer,
    SaleListSerializer,
    SaleSerializer,
    SaleStatisticsSerializer,
)
from customers.services import CustomerService, SaleService


class CustomerViewSet(viewsets.ModelViewSet):

    queryset = Customer.objects.select_related("user").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CustomerFilter
    search_fields = ["user__username", "user__email", "phone", "city"]
    ordering_fields = ["total_purchases", "total_spent", "loyalty_points", "created_at"]
    ordering = ["-total_spent"]

    def get_serializer_class(self):
        if self.action == ViewAction.REGISTER:
            return CustomerRegistrationSerializer
        elif self.action == ViewAction.LIST:
            return CustomerListSerializer
        return CustomerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if getattr(self, "swagger_fake_view", False):
            return queryset

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_permissions(self):

        if self.action == ViewAction.REGISTER:
            return [AllowAny()]
        elif self.action in [ViewAction.UPDATE, ViewAction.PARTIAL_UPDATE, ViewAction.DESTROY]:
            return [IsOwnerOrAdmin()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = CustomerService.register_user(
            username=serializer.validated_data["username"],
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
            phone=serializer.validated_data.get("phone", ""),
            country=serializer.validated_data.get("country", ""),
            city=serializer.validated_data.get("city", ""),
            address=serializer.validated_data.get("address", ""),
        )

        return Response(CustomerSerializer(customer).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = CustomerService.get_customer_by_user(request.user)
        if not customer:
            return Response({"error": "Customer profile not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(customer)
        return Response(serializer.data)

    @action(detail=False, methods=["patch"], permission_classes=[IsAuthenticated])
    def update_profile(self, request):
        customer = CustomerService.get_customer_by_user(request.user)
        if not customer:
            return Response({"error": "Customer profile not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = CustomerService.update_customer(customer, serializer.validated_data)
        return Response(self.get_serializer(updated).data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def my_purchases(self, request):
        customer = CustomerService.get_by_user(request.user)
        if not customer:
            return Response({"error": "Customer profile not found"}, status=status.HTTP_404_NOT_FOUND)

        purchases = SaleService.get_sales_by_customer(customer)
        serializer = SaleListSerializer(purchases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def statistics(self, request, pk=None):
        customer = self.get_object()
        stats = CustomerService.get_statistics(customer)
        serializer = CustomerStatisticsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def update_balance(self, request, pk=None):
        customer = self.get_object()
        amount = request.data.get("amount")

        if not amount:
            return Response({"error": "Amount parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = Decimal(str(amount))
        except (ValueError, TypeError):
            return Response({"error": "Invalid amount value"}, status=status.HTTP_400_BAD_REQUEST)

        updated = CustomerService.update_balance(customer, amount)
        serializer = self.get_serializer(updated)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def verify_email(self, request, pk=None):
        customer = self.get_object()
        verified = CustomerService.verify_email(customer)
        serializer = self.get_serializer(verified)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAdminUser])
    def vip_customers(self, request):
        vip_customers = CustomerService.get_vip_customers()
        serializer = self.get_serializer(vip_customers, many=True)
        return Response(serializer.data)


class SaleViewSet(viewsets.ModelViewSet):

    queryset = Sale.objects.select_related("dealership", "customer", "car_model").all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = SaleFilter
    search_fields = [
        "dealership__name",
        "customer__user__username",
        "car_model__brand",
        "car_model__model",
        "vin_number",
    ]
    ordering_fields = ["price", "discount_applied", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return SaleListSerializer
        return SaleSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        if getattr(self, "swagger_fake_view", False):
            return queryset

        if not self.request.user.is_staff:
            try:
                customer = CustomerService.get_customer_by_user(self.request.user)
                queryset = queryset.filter(customer=customer)
            except Customer.DoesNotExist:
                queryset = queryset.none()

        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)

        return queryset

    def get_permissions(self):

        if self.action in [ViewAction.CREATE, ViewAction.UPDATE, ViewAction.PARTIAL_UPDATE, ViewAction.DESTROY]:
            return [IsAdminUser()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        instance.soft_delete()

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        stats = SaleService.get_sales_statistics()
        serializer = SaleStatisticsSerializer(stats)
        return Response(serializer.data)
