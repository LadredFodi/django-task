"""Service layer for promotion operations and business logic."""

from django.db.models import Count, Sum, Avg, QuerySet
from django.utils import timezone
from typing import Optional, Any
from decimal import Decimal
from promotions.models import Promotion, PromotionDealership, PromotionSupplier


class PromotionService:
    """Service class for managing promotions."""

    @staticmethod
    def get_all_active_promotions() -> QuerySet[Promotion]:
        """Get all active promotions with related car models."""
        return Promotion.objects.prefetch_related('car_models').filter(is_active=True)
    
    @staticmethod
    def get_promotion_by_id(promotion_id: int) -> Optional[Promotion]:
        """Get promotion by ID if active."""
        try:
            return Promotion.objects.prefetch_related('car_models').get(
                id=promotion_id,
                is_active=True
            )
        except Promotion.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_now_promotions() -> QuerySet[Promotion]:
        """Get promotions that are currently active (within date range)."""
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).prefetch_related('car_models')
    
    @staticmethod
    def get_upcoming_promotions() -> QuerySet[Promotion]:
        """Get promotions that will start in the future."""
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__gt=now
        ).prefetch_related('car_models').order_by('start_date')
    
    @staticmethod
    def create_promotion(data: dict[str, Any]) -> Promotion:
        """Create new promotion with car models."""
        car_models = data.pop('car_models', [])
        promotion = Promotion.objects.create(**data)
        if car_models:
            promotion.car_models.set(car_models)
        return promotion
    
    @staticmethod
    def update_promotion(promotion: Promotion, data: dict[str, Any]) -> Promotion:
        """Update promotion with provided data."""
        car_models = data.pop('car_models', None)
        
        for key, value in data.items():
            setattr(promotion, key, value)
        promotion.save()
        
        if car_models is not None:
            promotion.car_models.set(car_models)
        
        return promotion
    
    @staticmethod
    def get_promotion_statistics(promotion: Promotion) -> dict:
        """Get comprehensive statistics for a promotion."""
        dealership_stats = promotion.dealership_promotions.filter(is_active=True).aggregate(
            total_dealerships=Count('id'),
            times_applied=Sum('times_applied'),
            total_discount=Sum('total_discount_amount'),
            avg_discount=Avg('discount_percent'),
        )
        
        supplier_stats = promotion.supplier_promotions.filter(is_active=True).aggregate(
            total_suppliers=Count('id'),
            times_applied=Sum('times_applied'),
            total_discount=Sum('total_discount_amount'),
            avg_discount=Avg('discount_percent'),
        )
        
        purchases_count = promotion.purchases.filter(is_active=True).count()
        sales_count = promotion.sales.filter(is_active=True).count()
        
        return {
            'times_used': promotion.times_used,
            'car_models_count': promotion.car_models.count(),
            'dealerships': dealership_stats,
            'suppliers': supplier_stats,
            'usage': {
                'purchases': purchases_count,
                'sales': sales_count,
            }
        }
    
    @staticmethod
    def check_applicable(promotion: Promotion, car_model_id: int = None, amount: Decimal = None) -> bool:
        """Check if promotion is applicable for given car model and amount."""

        now = timezone.now()
        
        if not promotion.is_active or promotion.start_date > now or promotion.end_date < now:
            return False
        
        if car_model_id and promotion.car_models.exists():
            if not promotion.car_models.filter(id=car_model_id).exists():
                return False
        
        if amount and promotion.min_purchase_amount:
            if amount < promotion.min_purchase_amount:
                return False
        
        return True


class PromotionDealershipService:
    """Service class for managing dealership-specific promotions."""

    @staticmethod
    def get_all_active_dealership_promotions() -> QuerySet[PromotionDealership]:
        return PromotionDealership.objects.select_related('promotion', 'dealership').filter(
            is_active=True
        )
    
    @staticmethod
    def get_dealership_promotions_by_dealership(dealership_id: int) -> QuerySet[PromotionDealership]:
        """Get all active promotions for a specific dealership."""
        return PromotionDealership.objects.filter(
            dealership_id=dealership_id,
            is_active=True
        ).select_related('promotion')
    
    @staticmethod
    def check_exists(promotion_id: int, dealership_id: int) -> bool:
        """Check if promotion-dealership relationship exists."""
        return PromotionDealership.objects.filter(
            promotion_id=promotion_id,
            dealership_id=dealership_id,
            is_active=True
        ).exists()
    
    @staticmethod
    def create_dealership_promotion(data: dict[str, Any]) -> PromotionDealership:
        """Create new dealership promotion relationship."""
        return PromotionDealership.objects.create(**data)
    
    @staticmethod
    def update_dealership_promotion(promo: PromotionDealership, data: dict[str, Any]) -> PromotionDealership:
        """Update dealership promotion with provided data."""
        for key, value in data.items():
            setattr(promo, key, value)
        promo.save()
        return promo
    
    @staticmethod
    def apply_promotion(promo: PromotionDealership, amount: Decimal) -> PromotionDealership:
        """Apply promotion and update usage statistics."""
        discount_amount = amount * (promo.discount_percent / 100)
        
        promo.times_applied += 1
        promo.total_discount_amount += discount_amount
        promo.save(update_fields=['times_applied', 'total_discount_amount', 'updated_at'])
        
        promo.promotion.times_used += 1
        promo.promotion.save(update_fields=['times_used', 'updated_at'])
        
        return promo
    
    @staticmethod
    def get_top_dealerships(limit: int = 10):
        """Get top dealerships by promotion usage."""
        return PromotionDealership.objects.filter(
            times_applied__gt=0,
            is_active=True
        ).select_related('dealership', 'promotion').order_by('-times_applied')[:limit]


class PromotionSupplierService:
    """Service class for managing supplier-specific promotions."""

    @staticmethod
    def get_all_active_supplier_promotions() -> QuerySet[PromotionSupplier]:
        """Get all active supplier promotions with related data."""
        return PromotionSupplier.objects.select_related('promotion', 'supplier').filter(
            is_active=True
        )
    
    @staticmethod
    def get_supplier_promotions_by_supplier(supplier_id: int) -> QuerySet[PromotionSupplier]:
        """Get all active promotions for a specific supplier."""
        return PromotionSupplier.objects.filter(
            supplier_id=supplier_id,
            is_active=True
        ).select_related('promotion')
    
    @staticmethod
    def check_exists(promotion_id: int, supplier_id: int) -> bool:
        """Check if promotion-supplier relationship exists."""
        return PromotionSupplier.objects.filter(
            promotion_id=promotion_id,
            supplier_id=supplier_id,
            is_active=True
        ).exists()
    
    @staticmethod
    def create_supplier_promotion(data: dict[str, Any]) -> PromotionSupplier:
        """Create new supplier promotion relationship."""
        return PromotionSupplier.objects.create(**data)
    
    @staticmethod
    def update_supplier_promotion(promo: PromotionSupplier, data: dict[str, Any]) -> PromotionSupplier:
        """Update supplier promotion with provided data."""
        for key, value in data.items():
            setattr(promo, key, value)
        promo.save()
        return promo
    
    @staticmethod
    def apply_promotion(promo: PromotionSupplier, amount: Decimal) -> PromotionSupplier:
        """Apply promotion and update usage statistics."""
        discount_amount = amount * (promo.discount_percent / 100)
        
        promo.times_applied += 1
        promo.total_discount_amount += discount_amount
        promo.save(update_fields=['times_applied', 'total_discount_amount', 'updated_at'])
        
        promo.promotion.times_used += 1
        promo.promotion.save(update_fields=['times_used', 'updated_at'])
        
        return promo
    
    @staticmethod
    def get_top_suppliers(limit: int = 10) -> QuerySet[PromotionSupplier]:
        """Get top suppliers by promotion usage."""
        return PromotionSupplier.objects.filter(
            times_applied__gt=0,
            is_active=True
        ).select_related('supplier', 'promotion').order_by('-times_applied')[:limit]
