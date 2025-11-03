from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from promotions.models import Promotion, PromotionDealership, PromotionSupplier
from promotions.serializers import (
    PromotionSerializer, PromotionListSerializer,
    PromotionDealershipSerializer,
    PromotionSupplierSerializer
)
from promotions.filters import PromotionFilter, PromotionDealershipFilter, PromotionSupplierFilter
from promotions.services import PromotionService, PromotionDealershipService, PromotionSupplierService
from config.permissions import IsAdminOrReadOnly, IsAdminUser


class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.prefetch_related('car_models').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PromotionFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'start_date', 'end_date', 'default_discount_percent', 'times_used', 'created_at']
    ordering = ['-start_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionListSerializer
        return PromotionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def perform_destroy(self, instance):
        instance.soft_delete()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        active_promotions = PromotionService.get_active_now_promotions()
        serializer = self.get_serializer(active_promotions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        upcoming_promotions = PromotionService.get_upcoming_promotions()
        serializer = self.get_serializer(upcoming_promotions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def dealerships(self, request, pk=None):
        promotion = self.get_object()
        dealership_promotions = promotion.dealership_promotions.filter(is_active=True)
        serializer = PromotionDealershipSerializer(dealership_promotions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def suppliers(self, request, pk=None):
        promotion = self.get_object()
        supplier_promotions = promotion.supplier_promotions.filter(is_active=True)
        serializer = PromotionSupplierSerializer(supplier_promotions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        promotion = self.get_object()
        stats = PromotionService.get_promotion_statistics(promotion)
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        instance = self.get_object()
        instance.restore()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class PromotionDealershipViewSet(viewsets.ModelViewSet):
    queryset = PromotionDealership.objects.select_related('promotion', 'dealership').all()
    serializer_class = PromotionDealershipSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PromotionDealershipFilter
    ordering_fields = ['discount_percent', 'times_applied', 'total_discount_amount', 'created_at']
    ordering = ['-times_applied']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def perform_destroy(self, instance):
        instance.soft_delete()
    
    @action(detail=False, methods=['get'])
    def top_dealerships(self, request)-> QuerySet[PromotionDealership]:
        top = PromotionDealershipService.get_top_dealerships(limit=10)
        serializer = self.get_serializer(top, many=True)
        return Response(serializer.data)


class PromotionSupplierViewSet(viewsets.ModelViewSet):
    queryset = PromotionSupplier.objects.select_related('promotion', 'supplier').all()
    serializer_class = PromotionSupplierSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PromotionSupplierFilter
    ordering_fields = ['discount_percent', 'times_applied', 'total_discount_amount', 'created_at']
    ordering = ['-times_applied']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def perform_destroy(self, instance):
        instance.soft_delete()
    
    @action(detail=False, methods=['get'])
    def top_suppliers(self, request):
        top = PromotionSupplierService.get_top_suppliers(limit=10)
        serializer = self.get_serializer(top, many=True)
        return Response(serializer.data)
