"""API views for customer offers and dealership matching."""
from enum import Enum

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from offers.models import Offer
from offers.serializers import OfferSerializer, OfferListSerializer, OfferCreateSerializer
from offers.filters import OfferFilter
from offers.services import OfferService
from config.permissions import IsAdminUser, IsEmailVerified, IsOwnerOrAdmin
from customers.models import Customer
from customers.services import CustomerService
from config.enums import ViewAction

class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing customer offers and dealership matching."""

    queryset = Offer.objects.select_related('customer', 'car_model', 'matched_dealership').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = OfferFilter
    search_fields = [
        'customer__user__username',
        'car_model__brand',
        'car_model__model',
        'matched_dealership__name'
    ]
    ordering_fields = ['max_price', 'status', 'created_at', 'processed_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == ViewAction.CREATE:
            return OfferCreateSerializer
        elif self.action == ViewAction.LIST:
            return OfferListSerializer
        return OfferSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if getattr(self, 'swagger_fake_view', False):
            return queryset
        
        if not self.request.user.is_staff:
            try:
                customer = self.request.user.customer_profile
                queryset = queryset.filter(customer=customer)
            except Customer.DoesNotExist:
                queryset = queryset.none()
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    def get_permissions(self):

        if self.action == ViewAction.CREATE:
            return [IsAuthenticated(), IsEmailVerified()]
        elif self.action in [ViewAction.UPDATE, ViewAction.PARTIAL_UPDATE, ViewAction.DESTROY]:
            return [IsOwnerOrAdmin()]
        elif self.action in [ViewAction.PROCESS, ViewAction.COMPLETE]:
            return [IsAdminUser()]
        elif self.action == ViewAction.CANCEL:
            return [IsAuthenticated()]
        return super().get_permissions()
    
    def perform_destroy(self, instance):

        instance.soft_delete()
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_offers(self, request):
        customer = CustomerService.get_customer_by_user(request.user)
        if not customer:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        offers = OfferService.get_offers_by_customer(customer)
        serializer = self.get_serializer(offers, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def pending(self, request):
        pending_offers = OfferService.get_pending_offers()
        serializer = self.get_serializer(pending_offers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def process(self, request, pk=None):
        offer = self.get_object()
        
        if offer.status != 'pending':
            return Response(
                {'error': 'Offer already processed or being processed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        processed = OfferService.process_offer(offer)
        serializer = self.get_serializer(processed)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def complete(self, request, pk=None):
        offer = self.get_object()
        
        if offer.status == 'completed':
            return Response(
                {'error': 'Offer already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        completed = OfferService.complete_offer(offer)
        serializer = self.get_serializer(completed)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        offer = self.get_object()
        
        if not request.user.is_staff:
            if offer.customer.user != request.user:
                return Response(
                    {'error': 'You do not have permission to cancel this offer'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if offer.status != 'pending':
                return Response(
                    {'error': 'You can only cancel pending offers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if offer.status in ['completed', 'cancelled']:
            return Response(
                {'error': 'You cannot cancel a completed or already cancelled offer'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cancelled = OfferService.cancel_offer(offer)
        serializer = self.get_serializer(cancelled)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def statistics(self, request):
        stats = OfferService.get_statistics()
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def search_results_detail(self, request, pk=None):

        offer = self.get_object()
        
        if not offer.search_results:
            return Response(
                {'message': 'Search results are not available yet'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(offer.search_results)
