from django.db.models import Count, Sum, Q, Avg, Min, QuerySet
from typing import Optional, Any
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from dealerships.services import PurchaseService

class SupplierService:
    
    @staticmethod
    def get_all_active_suppliers() -> QuerySet[Supplier]:
        return Supplier.objects.filter(is_active=True).annotate(
            total_cars=Count('supplier_cars', filter=Q(supplier_cars__is_active=True))
        )
    
    @staticmethod
    def get_supplier_by_id(supplier_id: int) -> Optional[Supplier]:
        try:
            return Supplier.objects.get(id=supplier_id, is_active=True)
        except Supplier.DoesNotExist:
            return None
    
    @staticmethod
    def create_supplier(data: dict[str, Any]) -> Supplier:
        return Supplier.objects.create(**data)
    
    @staticmethod
    def update_supplier(supplier: Supplier, data: dict[str, Any]) -> Supplier:
        for key, value in data.items():
            setattr(supplier, key, value)
        supplier.save()
        return supplier
    
    @staticmethod
    def get_supplier_statistics(supplier: Supplier) -> dict[str, Any]:
        return {
            'total_sales': supplier.total_sales,
            'total_revenue': float(supplier.total_revenue),
            'total_car_models': supplier.supplier_cars.filter(is_active=True).count(),
            'total_available_cars': supplier.supplier_cars.filter(is_active=True).aggregate(
                total=Sum('available_quantity')
            )['total'] or 0,
            'average_price': supplier.supplier_cars.filter(is_active=True).aggregate(
                avg=Avg('price')
            )['avg'] or 0,
            'partner_dealerships': supplier.supplier_discounts.filter(is_active=True).count(),
        }


class SupplierCarService:
    
    @staticmethod
    def get_all_active_supplier_cars() -> QuerySet[SupplierCar]:
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
        return SupplierCar.objects.create(**data)
    
    @staticmethod
    def update_supplier_car(supplier_car: SupplierCar, data: dict[str, Any]) -> SupplierCar:
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

