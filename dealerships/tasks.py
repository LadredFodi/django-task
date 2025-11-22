"""Celery tasks for dealership operations and automated processes."""

from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from celery import shared_task
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from cars.models import CarModel
from dealerships.models import Dealership, DealershipInventory, DealershipPreference, Purchase
from promotions.models import PromotionSupplier
from suppliers.models import Supplier, SupplierCar


@shared_task(name="config.tasks.dealership_purchase_cars")
def dealership_purchase_cars():
    """
    Celery task to automate car purchases for all dealerships.

    Analyzes demand and preferences for each dealership and makes
    automated purchase decisions from suppliers.

    Returns:
        dict: Summary with total purchases made.
    """
    active_dealerships = Dealership.objects.filter(is_active=True)
    total_purchases = 0

    for dealership in active_dealerships:
        try:
            purchases_made = _process_dealership_purchases(dealership)
            total_purchases += purchases_made
        except Exception:
            continue

    return {"total_purchases": total_purchases}


def _process_dealership_purchases(dealership: Dealership) -> int:
    """
    Process purchases for a single dealership.

    Args:
        dealership: Dealership instance to process.

    Returns:
        Number of successful purchases made.
    """
    try:
        preferences = dealership.preferences.filter(is_active=True).first()
    except Exception:
        preferences = None

    demand_analysis = _analyze_demand(dealership)

    models_to_purchase = _get_models_to_purchase(dealership, preferences, demand_analysis)

    purchases_count = 0

    for car_model_id, quantity_needed in models_to_purchase.items():
        try:
            best_supplier_offer = _find_best_supplier_offer(car_model_id, quantity_needed)

            if not best_supplier_offer:
                continue

            total_cost = best_supplier_offer["total_price"]
            if dealership.balance < total_cost:
                continue

            with transaction.atomic():
                purchase = _create_purchase(
                    dealership=dealership,
                    supplier_id=best_supplier_offer["supplier_id"],
                    car_model_id=car_model_id,
                    quantity=quantity_needed,
                    unit_price=best_supplier_offer["unit_price"],
                    total_price=total_cost,
                    discount_applied=best_supplier_offer.get("discount_percent", 0),
                    promotion_id=best_supplier_offer.get("promotion_id"),
                )

                if purchase:
                    purchases_count += 1

        except Exception:
            continue

    return purchases_count


def _analyze_demand(dealership: Dealership) -> Dict[int, int]:
    """
    Analyze sales demand for last 30 days.

    Args:
        dealership: Dealership to analyze.

    Returns:
        Dictionary mapping car_model_id to sales count.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)

    sales_stats = (
        dealership.sales.filter(is_active=True, created_at__gte=thirty_days_ago)
        .values("car_model_id")
        .annotate(sold_count=Count("id"))
        .order_by("-sold_count")
    )

    demand = {}
    for stat in sales_stats:
        demand[stat["car_model_id"]] = stat["sold_count"]

    return demand


def _get_models_to_purchase(
    dealership: Dealership, preferences: Optional[DealershipPreference], demand_analysis: Dict[int, int]
) -> Dict[int, int]:
    """
    Determine which models to purchase based on demand and preferences.

    Args:
        dealership: Dealership instance.
        preferences: Dealership preferences (optional).
        demand_analysis: Sales demand data.

    Returns:
        Dictionary mapping car_model_id to quantity needed.
    """
    models_to_purchase = {}

    current_inventory = dealership.inventory.filter(is_active=True).select_related("car_model")

    for car_model_id, sold_count in demand_analysis.items():
        inventory_item = current_inventory.filter(car_model_id=car_model_id).first()
        current_quantity = inventory_item.quantity if inventory_item else 0

        if sold_count >= 3 and current_quantity < 5:
            quantity_needed = min(5 - current_quantity, 10)
            models_to_purchase[car_model_id] = quantity_needed

    if preferences:
        preferred_models = CarModel.objects.filter(is_active=True)

        if preferences.preferred_brands:
            preferred_models = preferred_models.filter(brand__in=preferences.preferred_brands)

        if preferences.preferred_body_types:
            preferred_models = preferred_models.filter(body_type__in=preferences.preferred_body_types)

        if preferences.preferred_fuel_types:
            preferred_models = preferred_models.filter(fuel_type__in=preferences.preferred_fuel_types)

        for model in preferred_models[:3]:
            if model.id not in models_to_purchase:
                inventory_item = current_inventory.filter(car_model_id=model.id).first()
                if not inventory_item or inventory_item.quantity < 2:
                    models_to_purchase[model.id] = 2

    return models_to_purchase


def _find_best_supplier_offer(car_model_id: int, quantity: int) -> Optional[Dict[str, Any]]:
    """
    Find best supplier offer for specified car model and quantity.

    Considers base prices and active promotions.

    Args:
        car_model_id: ID of car model to purchase.
        quantity: Quantity needed.

    Returns:
        Dictionary with best offer details or None if no offers available.
    """
    now = timezone.now()

    supplier_cars = SupplierCar.objects.filter(
        car_model_id=car_model_id, is_active=True, supplier__is_active=True, available_quantity__gte=quantity
    ).select_related("supplier")

    if not supplier_cars.exists():
        return None

    best_offer = None
    best_final_price = None

    for supplier_car in supplier_cars:
        base_price = supplier_car.price
        discount_percent = Decimal("0")
        promotion_id = None

        active_promotions = PromotionSupplier.objects.filter(
            supplier=supplier_car.supplier,
            is_active=True,
            promotion__is_active=True,
            promotion__start_date__lte=now,
            promotion__end_date__gte=now,
        ).select_related("promotion")

        for promo_supplier in active_promotions:
            promotion = promo_supplier.promotion

            if promotion.car_models.exists():
                if not promotion.car_models.filter(id=car_model_id).exists():
                    continue

            if promo_supplier.discount_percent > discount_percent:
                discount_percent = promo_supplier.discount_percent
                promotion_id = promotion.id

        final_unit_price = base_price * (1 - discount_percent / 100)
        final_total_price = final_unit_price * quantity

        if best_final_price is None or final_total_price < best_final_price:
            best_final_price = final_total_price
            best_offer = {
                "supplier_id": supplier_car.supplier.id,
                "supplier_car_id": supplier_car.id,
                "unit_price": base_price,
                "final_unit_price": final_unit_price,
                "total_price": final_total_price,
                "discount_percent": discount_percent,
                "promotion_id": promotion_id,
            }

    return best_offer


def _create_purchase(
    dealership: Dealership,
    supplier_id: int,
    car_model_id: int,
    quantity: int,
    unit_price: Decimal,
    total_price: Decimal,
    discount_applied: Decimal = Decimal("0"),
    promotion_id: Optional[int] = None,
) -> Optional[Purchase]:
    """
    Create purchase transaction and update all related records.

    Updates: Purchase, Dealership balance, Inventory, SupplierCar, Supplier stats.

    Args:
        dealership: Buying dealership.
        supplier_id: Selling supplier ID.
        car_model_id: Car model ID.
        quantity: Number of cars.
        unit_price: Price per car.
        total_price: Total transaction price.
        discount_applied: Discount percentage applied.
        promotion_id: Applied promotion ID (optional).

    Returns:
        Created Purchase instance or None if failed.
    """
    try:
        with transaction.atomic():
            purchase = Purchase.objects.create(
                dealership=dealership,
                supplier_id=supplier_id,
                car_model_id=car_model_id,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                discount_applied=discount_applied,
                promotion_applied_id=promotion_id,
            )

            dealership.balance -= total_price
            dealership.save(update_fields=["balance", "updated_at"])

            inventory, created = DealershipInventory.objects.get_or_create(
                dealership=dealership,
                car_model_id=car_model_id,
                defaults={
                    "quantity": quantity,
                    "purchase_price": unit_price,
                    "selling_price": unit_price * Decimal("1.2"),
                },
            )

            if not created:
                total_cost = (inventory.purchase_price * inventory.quantity) + total_price
                new_quantity = inventory.quantity + quantity
                inventory.purchase_price = total_cost / new_quantity
                inventory.quantity = new_quantity
                inventory.save(update_fields=["quantity", "purchase_price", "updated_at"])

            supplier_car = SupplierCar.objects.get(supplier_id=supplier_id, car_model_id=car_model_id, is_active=True)
            supplier_car.available_quantity -= quantity
            supplier_car.times_sold += 1
            supplier_car.last_purchase_date = timezone.now()
            supplier_car.save(update_fields=["available_quantity", "times_sold", "last_purchase_date", "updated_at"])

            supplier = Supplier.objects.get(id=supplier_id)
            supplier.total_sales += quantity
            supplier.total_revenue += total_price
            supplier.save(update_fields=["total_sales", "total_revenue", "updated_at"])

            return purchase

    except Exception:
        return None
