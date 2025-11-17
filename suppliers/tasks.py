"""Celery tasks for supplier operations and price updates."""

from decimal import Decimal
from django.utils import timezone
from celery import shared_task


from dealerships.models import Dealership, Purchase
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from promotions.models import PromotionSupplier




@shared_task(name='config.tasks.update_supplier_preferences')
def update_supplier_preferences():
    """
    Celery task to update dealership supplier preferences.

    Analyzes current inventory and compares with alternative supplier offers
    to identify potential cost savings.

    Returns:
        dict: Summary with count of dealerships that had preference updates.
    """
    active_dealerships = Dealership.objects.filter(is_active=True)
    updates_count = 0
    
    for dealership in active_dealerships:
        try:
            updated = _update_dealership_supplier_preferences(dealership)
            if updated:
                updates_count += 1
        except Exception as e:
            continue
    
    return {'updates_count': updates_count}


def _update_dealership_supplier_preferences(dealership: Dealership) -> bool:
    """
    Update supplier preferences for a single dealership.

    Args:
        dealership: Dealership instance to update.

    Returns:
        True if better supplier alternatives were found, False otherwise.
    """
    inventory_models = dealership.inventory.filter(
        is_active=True,
        quantity__gt=0
    ).values_list('car_model_id', flat=True)
    
    if not inventory_models:
        return False
    
    updated = False
    
    for car_model_id in inventory_models:
        current_inventory = dealership.inventory.get(car_model_id=car_model_id)
        current_purchase_price = current_inventory.purchase_price
    
        supplier_offers = SupplierCar.objects.filter(
            car_model_id=car_model_id,
            is_active=True,
            supplier__is_active=True,
            available_quantity__gt=0
        ).select_related('supplier')
        
        best_alternative = None
        best_price = current_purchase_price
        
        for supplier_car in supplier_offers:
            potential_price = _calculate_potential_price(
                dealership, supplier_car.supplier, supplier_car.price
            )
            
            if potential_price < best_price * Decimal('0.95'):
                best_price = potential_price
                best_alternative = {
                    'supplier': supplier_car.supplier,
                    'price': potential_price,
                    'car_model_id': car_model_id
                }
        
        if best_alternative:
            updated = True
    
    return updated


def _calculate_potential_price(
    dealership: Dealership, supplier: Supplier, base_price: Decimal
) -> Decimal:
    """
    Calculate potential price from a supplier including promotions and discounts.

    Args:
        dealership: Dealership that would purchase.
        supplier: Supplier offering the car.
        base_price: Base price before discounts.

    Returns:
        Final price after applying all applicable discounts.
    """
    now = timezone.now()
    final_price = base_price
    
    active_promotions = PromotionSupplier.objects.filter(
        supplier=supplier,
        is_active=True,
        promotion__is_active=True,
        promotion__start_date__lte=now,
        promotion__end_date__gte=now
    ).order_by('-discount_percent').first()
    
    if active_promotions:
        discount = active_promotions.discount_percent
        final_price = base_price * (1 - discount / 100)
    
    try:
        loyalty_discount = SupplierDiscount.objects.get(
            supplier=supplier,
            dealership=dealership,
            is_active=True
        )
        
        if loyalty_discount.is_applied:
            loyalty_price = base_price * (1 - loyalty_discount.discount_percent / 100)
            final_price = min(final_price, loyalty_price)
        else:
            purchase_count = Purchase.objects.filter(
                dealership=dealership,
                supplier=supplier,
                is_active=True
            ).count()
            remaining = loyalty_discount.min_purchases - purchase_count
            if 0 < remaining <= 2:
                potential_discount = loyalty_discount.discount_percent * Decimal('0.5')
                potential_price = base_price * (1 - potential_discount / 100)
                final_price = min(final_price, potential_price)
    
    except Exception:
        pass
    
    return final_price

