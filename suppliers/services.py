"""Service layer for supplier operations and business logic."""

from django.db.models import Count, Sum, Q, Avg, Min, QuerySet
from typing import Optional, Any
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from dealerships.models import Purchase
from dealerships.services import PurchaseService
from django.utils import timezone

class SupplierService:
    """Service class for supplier management operations."""
    @staticmethod
    def get_all_active_suppliers() -> QuerySet[Supplier]:
        """Get all active suppliers with car count annotation."""
        return Supplier.objects.filter(is_active=True).annotate(
            total_cars=Count('supplier_cars', filter=Q(supplier_cars__is_active=True))
        )
    
    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[Supplier]:
        """Get supplier by ID if active."""
        try:
            return Supplier.objects.get(id=supplier_id, is_active=True)
        except Supplier.DoesNotExist:
            return None
    
    @staticmethod
    def create_supplier(data: dict[str, Any]) -> Supplier:
        """Create new supplier."""
        return Supplier.objects.create(**data)
    
    @staticmethod
    def update_supplier(supplier: Supplier, data: dict[str, Any]) -> Supplier:
        """Update supplier with provided data."""
        for key, value in data.items():
            setattr(supplier, key, value)
        supplier.save()
        return supplier
    
    @staticmethod
    def get_supplier_statistics(supplier: Supplier) -> dict[str, Any]:

        
        catalog_stats = supplier.supplier_cars.filter(is_active=True).aggregate(
            total_models=Count('id'),
            total_available=Sum('available_quantity'),
            avg_price=Avg('price'),
        )
        
        purchases_stats = Purchase.objects.filter(
            supplier=supplier,
            is_active=True
        ).aggregate(
            total_orders=Count('id'),
            total_quantity=Sum('quantity'),
            total_revenue=Sum('total_price'),
            avg_order_value=Avg('total_price'),
        )
        
        partner_stats = supplier.loyalty_discounts.filter(is_active=True).aggregate(
            total_partners=Count('id'),
            active_discounts=Count('id', filter=Q(is_applied=True)),
        )
        
        top_partner_dealerships = list(
            Purchase.objects.filter(supplier=supplier, is_active=True)
            .values('dealership__name', 'dealership__city')
            .annotate(
                orders_count=Count('id'),
                total_quantity=Sum('quantity'),
                total_revenue=Sum('total_price')
            )
            .order_by('-total_revenue')[:10]
        )
        
        top_selling_models = list(
            Purchase.objects.filter(supplier=supplier, is_active=True)
            .values('car_model__brand', 'car_model__model', 'car_model__year')
            .annotate(
                orders_count=Count('id'),
                total_quantity=Sum('quantity')
            )
            .order_by('-total_quantity')[:10]
        )
        
        now = timezone.now()
        active_promotions = list(
            supplier.promotions.filter(
                is_active=True,
                promotion__is_active=True,
                promotion__start_date__lte=now,
                promotion__end_date__gte=now
            )
            .values('promotion__name', 'discount_percent', 'times_applied')
            .order_by('-discount_percent')[:10]
        )
        
        return {
            'supplier_id': supplier.id,
            'supplier_name': supplier.name,
            'rating': float(supplier.rating),
            'total_sales': purchases_stats['total_quantity'] or 0,
            'total_revenue': float(purchases_stats['total_revenue'] or 0),
            'avg_order_value': float(purchases_stats['avg_order_value'] or 0),
            'total_car_models': catalog_stats['total_models'] or 0,
            'total_available_cars': catalog_stats['total_available'] or 0,
            'average_price': float(catalog_stats['avg_price'] or 0),
            'partner_dealerships': partner_stats['total_partners'] or 0,
            'active_discounts': partner_stats['active_discounts'] or 0,
            'top_partner_dealerships': top_partner_dealerships,
            'top_selling_models': top_selling_models,
            'active_promotions': active_promotions,
        }


class SupplierCarService:
    """Service class for managing cars offered by suppliers."""

    @staticmethod
    def get_all_active_supplier_cars() -> QuerySet[SupplierCar]:
        """Get all active supplier cars with related data."""
        return SupplierCar.objects.select_related('supplier', 'car_model').filter(
            is_active=True,
            supplier__is_active=True
        )
    
    @staticmethod
    def get_supplier_cars_by_supplier(supplier_id: int) -> QuerySet[SupplierCar]:
        return SupplierCar.objects.filter(
            supplier_id=supplier_id,
            is_active=True
        ).select_related('car_model')
    
    @staticmethod
    def create_supplier_car(data: dict[str, Any]) -> SupplierCar:
        """Create new supplier car entry."""
        return SupplierCar.objects.create(**data)
    
    @staticmethod
    def update_supplier_car(supplier_car: SupplierCar, data: dict[str, Any]) -> SupplierCar:
        """Update supplier car with provided data."""
        for key, value in data.items():
            setattr(supplier_car, key, value)
        supplier_car.save()
        return supplier_car
    
    @staticmethod
    def get_best_prices() -> QuerySet[SupplierCar]:
        best_prices = SupplierCar.objects.filter(is_active=True).values('car_model').annotate(
            min_price=Min('price')
        )
        
        car_ids = []
        for item in best_prices:
            car = SupplierCar.objects.filter(
                car_model=item['car_model'],
                price=item['min_price'],
                is_active=True
            ).first()
            if car:
                car_ids.append(car.id)
        
        return SupplierCar.objects.filter(id__in=car_ids).select_related('supplier', 'car_model')


class SupplierDiscountService:
    
    @staticmethod
    def get_all_active_supplier_discounts() -> QuerySet[SupplierDiscount]:
        return SupplierDiscount.objects.select_related('supplier', 'dealership').filter(
            is_active=True
        )
    
    @staticmethod
    def create_supplier_discount(data: dict[str, Any]) -> SupplierDiscount:
        return SupplierDiscount.objects.create(**data)
    
    @staticmethod
    def update_discount(discount: SupplierDiscount, data: dict[str, Any]) -> SupplierDiscount:
        """Update supplier discount with provided data."""
        for key, value in data.items():
            setattr(discount, key, value)
        discount.save()
        return discount
    
    @staticmethod
    def check_and_apply_discount(supplier_id: int, dealership_id: int) -> Optional[SupplierDiscount]:
        try:
            discount = SupplierDiscount.objects.get(
                supplier_id=supplier_id,
                dealership_id=dealership_id,
                is_active=True
            )
            
            purchase_count = PurchaseService.get_purchase_count(supplier_id, dealership_id)
            
            if purchase_count >= discount.min_purchases:
                discount.is_applied = True
                discount.save()
                return discount
            
            return None
        except SupplierDiscount.DoesNotExist:
            return None

