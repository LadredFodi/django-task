from django.db.models import Count, Sum, Avg
from django.utils import timezone
from typing import Optional, Any, QuerySet
from decimal import Decimal
from promotions.models import Promotion, PromotionDealership, PromotionSupplier


class PromotionService:
    
    @staticmethod
    def get_all_active_promotions() -> QuerySet[Promotion]:
        return Promotion.objects.prefetch_related('car_models').filter(is_active=True)
    
    @staticmethod
    def get_promotion_by_id(promotion_id: int) -> Optional[Promotion]:
        try:
            return Promotion.objects.prefetch_related('car_models').get(
                id=promotion_id,
                is_active=True
            )
        except Promotion.DoesNotExist:
            return None
    
    @staticmethod
    def get_active_now_promotions() -> QuerySet[Promotion]:
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__lte=now,
            end_date__gte=now
        ).prefetch_related('car_models')
    
    @staticmethod
    def get_upcoming_promotions() -> QuerySet[Promotion]:
        now = timezone.now()
        return Promotion.objects.filter(
            is_active=True,
            start_date__gt=now
        ).prefetch_related('car_models').order_by('start_date')
    
    @staticmethod
    def create_promotion(data: dict[str, Any]) -> Promotion:
        car_models = data.pop('car_models', [])
        promotion = Promotion.objects.create(**data)
        if car_models:
            promotion.car_models.set(car_models)
        return promotion
    
    @staticmethod
    def update_promotion(promotion: Promotion, data: dict[str, Any]) -> Promotion:
        car_models = data.pop('car_models', None)
        
        for key, value in data.items():
            setattr(promotion, key, value)
        promotion.save()
        
        if car_models is not None:
            promotion.car_models.set(car_models)
        
        return promotion
    
    @staticmethod
    def get_promotion_statistics(promotion: Promotion) -> dict:
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

    @staticmethod
    def get_all_active_dealership_promotions() -> QuerySet[PromotionDealership]:
        return PromotionDealership.objects.select_related('promotion', 'dealership').filter(
            is_active=True
        )
    
    @staticmethod
    def get_dealership_promotions_by_dealership(dealership_id: int) -> QuerySet[PromotionDealership]:
        return PromotionDealership.objects.filter(
            dealership_id=dealership_id,
            is_active=True
        ).select_related('promotion')
    
    @staticmethod
    def check_exists(promotion_id: int, dealership_id: int) -> bool:
        return PromotionDealership.objects.filter(
            promotion_id=promotion_id,
            dealership_id=dealership_id,
            is_active=True
        ).exists()
    
    @staticmethod
    def create_dealership_promotion(data: dict[str, Any]) -> PromotionDealership:
        return PromotionDealership.objects.create(**data)
    
    @staticmethod
    def update_dealership_promotion(promo: PromotionDealership, data: dict[str, Any]) -> PromotionDealership:
        for key, value in data.items():
            setattr(promo, key, value)
        promo.save()
        return promo
    
    @staticmethod
    def apply_promotion(promo: PromotionDealership, amount: Decimal) -> PromotionDealership:
        discount_amount = amount * (promo.discount_percent / 100)
        
        promo.times_applied += 1
        promo.total_discount_amount += discount_amount
        promo.save(update_fields=['times_applied', 'total_discount_amount', 'updated_at'])
        
        promo.promotion.times_used += 1
        promo.promotion.save(update_fields=['times_used', 'updated_at'])
        
        return promo
    
    @staticmethod
    def get_top_dealerships(limit: int = 10):
        return PromotionDealership.objects.filter(
            times_applied__gt=0,
            is_active=True
        ).select_related('dealership', 'promotion').order_by('-times_applied')[:limit]


class PromotionSupplierService:
    
    @staticmethod
    def get_all_active_supplier_promotions() -> QuerySet[PromotionSupplier]:
        return PromotionSupplier.objects.select_related('promotion', 'supplier').filter(
            is_active=True
        )
    
    @staticmethod
    def get_supplier_promotions_by_supplier(supplier_id: int) -> QuerySet[PromotionSupplier]:
        return PromotionSupplier.objects.filter(
            supplier_id=supplier_id,
            is_active=True
        ).select_related('promotion')
    
    @staticmethod
    def check_exists(promotion_id: int, supplier_id: int) -> bool:
        return PromotionSupplier.objects.filter(
            promotion_id=promotion_id,
            supplier_id=supplier_id,
            is_active=True
        ).exists()
    
    @staticmethod
    def create_supplier_promotion(data: dict[str, Any]) -> PromotionSupplier:
        return PromotionSupplier.objects.create(**data)
    
    @staticmethod
    def update_supplier_promotion(promo: PromotionSupplier, data: dict[str, Any]) -> PromotionSupplier:
        for key, value in data.items():
            setattr(promo, key, value)
        promo.save()
        return promo
    
    @staticmethod
    def apply_promotion(promo: PromotionSupplier, amount: Decimal) -> PromotionSupplier:
        discount_amount = amount * (promo.discount_percent / 100)
        
        promo.times_applied += 1
        promo.total_discount_amount += discount_amount
        promo.save(update_fields=['times_applied', 'total_discount_amount', 'updated_at'])
        
        promo.promotion.times_used += 1
        promo.promotion.save(update_fields=['times_used', 'updated_at'])
        
        return promo
    
    @staticmethod
    def get_top_suppliers(limit: int = 10) -> QuerySet[PromotionSupplier]:
        return PromotionSupplier.objects.filter(
            times_applied__gt=0,
            is_active=True
        ).select_related('supplier', 'promotion').order_by('-times_applied')[:limit]
