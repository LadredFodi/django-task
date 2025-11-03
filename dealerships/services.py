from django.db.models import Count, Sum, Avg, Q, F
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from typing import Optional, Tuple, Any, QuerySet
from decimal import Decimal
from dealerships.models import Dealership, DealershipPreference, DealershipInventory, Purchase


class DealershipService:

    @staticmethod
    def get_all_active_dealerships() -> QuerySet[Dealership]:
        return Dealership.objects.filter(is_active=True)
    
    @staticmethod
    def get_dealership_by_id(dealership_id: int) -> Optional[Dealership]:
        try:
            return Dealership.objects.get(id=dealership_id, is_active=True)
        except Dealership.DoesNotExist:
            return None
    
    @staticmethod
    def create_dealership(data: dict[str, Any]) -> Dealership:
        return Dealership.objects.create(**data)
    
    @staticmethod
    def update_dealership(dealership: Dealership, data: dict[str, Any]) -> Dealership:
        for key, value in data.items():
            setattr(dealership, key, value)
        dealership.save()
        return dealership
    
    @staticmethod
    def update_balance(dealership: Dealership, amount: Decimal) -> Dealership:
        dealership.balance += amount
        dealership.save(update_fields=['balance', 'updated_at'])
        return dealership
    
    @staticmethod
    def get_dealership_statistics(dealership: Dealership) -> dict:
        inventory_stats = dealership.inventory.filter(is_active=True).aggregate(
            total_cars=Sum('quantity'),
            total_models=Count('id'),
            avg_selling_price=Avg('selling_price'),
        )
        
        sales_stats = dealership.sales.filter(is_active=True).aggregate(
            total_sales_count=Count('id'),
            total_sales_revenue=Sum('price'),
            avg_sale_price=Avg('price'),
        )
        
        unique_customers = dealership.sales.filter(is_active=True).values('customer').distinct().count()
        
        return {
            'balance': float(dealership.balance),
            'total_sales': dealership.total_sales,
            'total_revenue': float(dealership.total_revenue),
            'total_profit': float(dealership.total_profit),
            'inventory': {
                'total_cars': inventory_stats['total_cars'] or 0,
                'total_models': inventory_stats['total_models'] or 0,
                'avg_selling_price': float(inventory_stats['avg_selling_price'] or 0),
            },
            'sales': {
                'total_count': sales_stats['total_sales_count'] or 0,
                'total_revenue': float(sales_stats['total_sales_revenue'] or 0),
                'avg_price': float(sales_stats['avg_sale_price'] or 0),
                'unique_customers': unique_customers,
            },
        }
    
    @staticmethod
    def find_nearby(latitude: float, longitude: float, radius: float = 50) -> QuerySet[Dealership]:
        point = Point(longitude, latitude, srid=4326)
        return Dealership.objects.filter(
            is_active=True,
            location__distance_lte=(point, Distance(km=radius))
        ).annotate(
            distance=Distance('location', point)
        ).order_by('distance')


class DealershipInventoryService:

    @staticmethod
    def get_all_active_inventory() -> QuerySet[DealershipInventory]:
        return DealershipInventory.objects.select_related('dealership', 'car_model').filter(
            is_active=True,
            dealership__is_active=True
        )
    
    @staticmethod
    def get_inventory_by_dealership(dealership_id: int) -> QuerySet[DealershipInventory]:
        return DealershipInventory.objects.filter(
            dealership_id=dealership_id,
            is_active=True
        ).select_related('car_model')
    
    @staticmethod
    def get_available_inventory() -> QuerySet[DealershipInventory]:
        return DealershipInventory.objects.filter(
            is_active=True,
            quantity__gt=0
        ).select_related('dealership', 'car_model')
    
    @staticmethod
    def get_popular_inventory(limit: int = 20) -> QuerySet[DealershipInventory]:
        return DealershipInventory.objects.filter(
            is_active=True,
            times_sold__gt=0
        ).select_related('dealership', 'car_model').order_by('-times_sold')[:limit]
    
    @staticmethod
    def create_inventory_item(data: dict[str, Any]) -> DealershipInventory:
        return DealershipInventory.objects.create(**data)
    
    @staticmethod
    def update_inventory_item(inventory: DealershipInventory, data: dict) -> DealershipInventory:
        for key, value in data.items():
            setattr(inventory, key, value)
        inventory.save()
        return inventory
    
    @staticmethod
    def decrease_quantity(inventory: DealershipInventory, amount: int = 1) -> DealershipInventory:
        if inventory.quantity >= amount:
            inventory.quantity -= amount
            inventory.times_sold += 1
            inventory.save(update_fields=['quantity', 'times_sold', 'updated_at'])
        return inventory
    
    @staticmethod
    def increase_quantity(inventory: DealershipInventory, amount: int) -> DealershipInventory:
        inventory.quantity += amount
        inventory.save(update_fields=['quantity', 'updated_at'])
        return inventory


class PurchaseService:
    
    @staticmethod
    def get_all_active_purchases() -> QuerySet[Purchase]:
        return Purchase.objects.select_related('dealership', 'supplier', 'car_model').filter(
            is_active=True
        )
    
    @staticmethod
    def get_purchases_by_dealership(dealership_id: int) -> QuerySet[Purchase]:
        return Purchase.objects.filter(
            dealership_id=dealership_id,
            is_active=True
        ).select_related('supplier', 'car_model').order_by('-created_at')
    
    @staticmethod
    def create_purchase(data: dict[str, Any]) -> Purchase:
        purchase = Purchase.objects.create(**data)
        
        inventory, created = DealershipInventory.objects.get_or_create(
            dealership=purchase.dealership,
            car_model=purchase.car_model,
            defaults={
                'quantity': purchase.quantity,
                'purchase_price': purchase.unit_price,
                'selling_price': purchase.unit_price * Decimal('1.2'),
            }
        )
        
        if not created:
            total_cost = (inventory.purchase_price * inventory.quantity) + purchase.total_price
            new_quantity = inventory.quantity + purchase.quantity
            inventory.purchase_price = total_cost / new_quantity
            inventory.quantity = new_quantity
            inventory.save()
        
        purchase.dealership.balance -= purchase.total_price
        purchase.dealership.save(update_fields=['balance', 'updated_at'])
        
        return purchase
    
    @staticmethod
    def get_purchase_count(supplier_id: int, dealership_id: int) -> int:
        return Purchase.objects.filter(
            supplier_id=supplier_id,
            dealership_id=dealership_id,
            is_active=True
        ).count()
    
    @staticmethod
    def get_statistics() -> dict[str, Any]:
        return Purchase.objects.filter(is_active=True).aggregate(
            total_purchases=Count('id'),
            total_quantity=Sum('quantity'),
            total_amount=Sum('total_price'),
            avg_unit_price=Avg('unit_price'),
        )


class DealershipPreferenceService:
    
    @staticmethod
    def get_preference_by_dealership(dealership_id: int) -> Optional[DealershipPreference]:
        try:
            return DealershipPreference.objects.get(
                dealership_id=dealership_id,
                is_active=True
            )
        except DealershipPreference.DoesNotExist:
            return None
    
    @staticmethod
    def create_preference(data: dict[str, Any]) -> DealershipPreference:
        return DealershipPreference.objects.create(**data)
    
    @staticmethod
    def update_preference(preference: DealershipPreference, data: dict[str, Any]) -> DealershipPreference:
        for key, value in data.items():
            setattr(preference, key, value)
        preference.save()
        return preference

