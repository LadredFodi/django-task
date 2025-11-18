from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from cars.filters import CarModelFilter
from cars.models import CarModel
from cars.serializers import CarModelListSerializer, CarModelSerializer
from cars.services import CarModelService
from config.enums import ViewAction
from config.permissions import IsAdminOrReadOnly


class CarModelViewSet(viewsets.ModelViewSet):

    queryset = CarModel.objects.all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CarModelFilter
    search_fields = ["brand", "model", "color", "description"]
    ordering_fields = ["year", "brand", "model", "engine_volume", "horsepower", "created_at"]
    ordering = ["-year", "brand", "model"]

    def get_serializer_class(self):
        if self.action == ViewAction.LIST:
            return CarModelListSerializer
        return CarModelSerializer

    def get_queryset(self):
        if not self.request.user.is_staff:
            return CarModelService.get_all_active_cars()
        return super().get_queryset()

    def perform_destroy(self, instance):
        CarModelService.soft_delete_car_model(instance)

    @action(detail=False, methods=["get"])
    def popular(self, request):
        popular_cars = CarModelService.get_popular_models(limit=10)
        serializer = self.get_serializer(popular_cars, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def brands(self, request):
        brands = CarModelService.get_all_brands()
        return Response(brands)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        instance = self.get_object()
        restored = CarModelService.restore_car_model(instance)
        serializer = self.get_serializer(restored)
        return Response(serializer.data)
