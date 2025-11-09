from django.db.models import Count, Avg
from django.utils import timezone
from typing import Optional, List, Dict, Any
from django.db.models import QuerySet
from offers.models import Offer
from customers.models import Customer
from dealerships.models import DealershipInventory


class OfferService:

    @staticmethod
    def get_all_active_offers() -> QuerySet[Offer]:
        return Offer.objects.select_related('customer', 'car_model', 'matched_dealership').filter(
            is_active=True
        )
    
    @staticmethod
    def get_offer_by_id(offer_id: int) -> Optional[Offer]:
        try:
            return Offer.objects.select_related('customer', 'car_model', 'matched_dealership').get(
                id=offer_id,
                is_active=True
            )
        except Offer.DoesNotExist:
            return None
    
    @staticmethod
    def get_offers_by_customer(customer: Customer) -> QuerySet[Offer]:
        return Offer.objects.filter(
            customer=customer,
            is_active=True
        ).select_related('car_model', 'matched_dealership').order_by('-created_at')
    
    @staticmethod
    def get_pending_offers() -> QuerySet[Offer]:
        return Offer.objects.filter(
            status='pending',
            is_active=True
        ).select_related('customer', 'car_model')
    
    @staticmethod
    def create_offer(customer: Customer, car_model_id: int, max_price: float, **kwargs: Any) -> Offer:
        offer = Offer.objects.create(
            customer=customer,
            car_model_id=car_model_id,
            max_price=max_price,
            **kwargs
        )
        
        OfferService.search_matching_dealerships(offer)
        
        return offer
    
    @staticmethod
    def search_matching_dealerships(offer: Offer) -> List[Dict[str, Any]]:
        matching_inventory = DealershipInventory.objects.filter(
            car_model=offer.car_model,
            selling_price__lte=offer.max_price,
            quantity__gt=0,
            is_active=True,
            dealership__is_active=True
        ).select_related('dealership').order_by('selling_price')
        
        results = []
        for inventory in matching_inventory:
            results.append({
                'dealership_id': inventory.dealership.id,
                'dealership_name': inventory.dealership.name,
                'price': float(inventory.selling_price),
                'quantity': inventory.quantity,
                'location': {
                    'city': inventory.dealership.city,
                    'country': str(inventory.dealership.country),
                }
            })
        
        offer.search_results = {'matches': results, 'total_found': len(results)}
        
        if results:
            offer.matched_dealership_id = results[0]['dealership_id']
            offer.matched_price = results[0]['price']
        
        offer.save(update_fields=['search_results', 'matched_dealership', 'matched_price', 'updated_at'])
        
        return results
    
    @staticmethod
    def process_offer(offer: Offer) -> Offer:
        offer.status = 'processing'
        offer.processed_at = timezone.now()
        offer.save(update_fields=['status', 'processed_at', 'updated_at'])
        
        OfferService.search_matching_dealerships(offer)
        
        return offer
    
    @staticmethod
    def complete_offer(offer: Offer) -> Offer:
        offer.status = 'completed'
        offer.completed_at = timezone.now()
        offer.save(update_fields=['status', 'completed_at', 'updated_at'])
        return offer
    
    @staticmethod
    def cancel_offer(offer: Offer) -> Offer:
        offer.status = 'cancelled'
        offer.save(update_fields=['status', 'updated_at'])
        return offer
    
    @staticmethod
    def expire_old_offers() -> int:
        now = timezone.now()
        expired_count = Offer.objects.filter(
            status__in=['pending', 'processing'],
            expires_at__lt=now,
            is_active=True
        ).update(status='expired', updated_at=now)
        
        return expired_count
    
    @staticmethod
    def get_statistics() -> dict:
        queryset = Offer.objects.filter(is_active=True)
        
        total_stats = queryset.aggregate(
            total_offers=Count('id'),
            avg_max_price=Avg('max_price'),
        )
        
        status_stats = {}
        for status_code, status_name in Offer.STATUS_CHOICES:
            count = queryset.filter(status=status_code).count()
            status_stats[status_code] = {
                'name': status_name,
                'count': count
            }
        
        top_models = list(
            queryset.values('car_model__brand', 'car_model__model')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        top_dealerships = list(
            queryset.filter(matched_dealership__isnull=False)
            .values('matched_dealership__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        return {
            'total': total_stats,
            'by_status': status_stats,
            'top_models': top_models,
            'top_dealerships': top_dealerships,
        }

