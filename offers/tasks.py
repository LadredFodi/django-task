"""Celery tasks for automated offer processing and matching."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from customers.models import Sale
from dealerships.models import Dealership, DealershipInventory
from offers.models import Offer


@shared_task(name="config.tasks.process_customer_offer")
def process_customer_offer(offer_id: int):
    """
    Celery task to process a single customer offer.

    Finds matching dealerships, selects the best match, and executes the purchase
    if customer has sufficient funds.

    Args:
        offer_id: ID of the offer to process.

    Returns:
        dict: Result dictionary with success status and details.
    """

    try:
        offer = Offer.objects.select_related("customer__user", "car_model").get(id=offer_id, is_active=True)
    except Offer.DoesNotExist:
        return {"success": False, "error": "Offer not found"}

    if offer.status != "pending":
        return {"success": False, "error": f"Offer status is {offer.status}"}

    offer.status = "processing"
    offer.processed_at = timezone.now()
    offer.save(update_fields=["status", "processed_at", "updated_at"])

    try:
        matching_dealerships = _find_matching_dealerships(offer)

        if not matching_dealerships:
            offer.status = "cancelled"
            offer.notes = "No matching dealerships found"
            offer.save(update_fields=["status", "notes", "updated_at"])
            return {"success": False, "error": "No matching dealerships"}

        offer.search_results = {
            "matches": matching_dealerships,
            "total_found": len(matching_dealerships),
            "search_date": timezone.now().isoformat(),
        }
        offer.matched_dealership_id = matching_dealerships[0]["dealership_id"]
        offer.matched_price = matching_dealerships[0]["final_price"]
        offer.save(update_fields=["search_results", "matched_dealership", "matched_price", "updated_at"])

        customer = offer.customer
        if customer.balance < Decimal(str(matching_dealerships[0]["final_price"])):
            offer.status = "cancelled"
            offer.notes = "Insufficient customer balance"
            offer.save(update_fields=["status", "notes", "updated_at"])
            return {"success": False, "error": "Insufficient balance"}

        sale = _execute_purchase(offer, matching_dealerships[0])

        if sale:
            offer.status = "completed"
            offer.completed_at = timezone.now()
            offer.save(update_fields=["status", "completed_at", "updated_at"])
            return {"success": True, "sale_id": sale.id}
        else:
            offer.status = "cancelled"
            offer.notes = "Failed to execute purchase"
            offer.save(update_fields=["status", "notes", "updated_at"])
            return {"success": False, "error": "Failed to execute purchase"}

    except Exception as e:
        offer.status = "cancelled"
        offer.notes = f"Error: {str(e)}"
        offer.save(update_fields=["status", "notes", "updated_at"])
        return {"success": False, "error": str(e)}


def _find_matching_dealerships(offer: Offer) -> List[Dict[str, Any]]:
    """
    Find dealerships that can fulfill the offer within the price limit.

    Args:
        offer: Offer instance to match.

    Returns:
        List of matching dealerships sorted by final price (lowest first).
    """

    now = timezone.now()

    matching_inventory = DealershipInventory.objects.filter(
        car_model=offer.car_model, quantity__gt=0, is_active=True, dealership__is_active=True
    ).select_related("dealership")

    results = []

    for inventory in matching_inventory:
        base_price = inventory.selling_price
        discount_percent = Decimal("0")
        promotion_id = None

        active_promotions = inventory.dealership.promotions.filter(
            is_active=True, promotion__is_active=True, promotion__start_date__lte=now, promotion__end_date__gte=now
        ).select_related("promotion")

        for promo_dealership in active_promotions:
            promotion = promo_dealership.promotion

            if promotion.car_models.exists():
                if not promotion.car_models.filter(id=offer.car_model.id).exists():
                    continue

            if promo_dealership.discount_percent > discount_percent:
                discount_percent = promo_dealership.discount_percent
                promotion_id = promotion.id

        final_price = base_price * (1 - discount_percent / 100)

        if final_price <= offer.max_price:
            results.append(
                {
                    "dealership_id": inventory.dealership.id,
                    "dealership_name": inventory.dealership.name,
                    "dealership_city": inventory.dealership.city,
                    "dealership_country": str(inventory.dealership.country),
                    "inventory_id": inventory.id,
                    "base_price": float(base_price),
                    "discount_percent": float(discount_percent),
                    "final_price": float(final_price),
                    "quantity_available": inventory.quantity,
                    "promotion_id": promotion_id,
                }
            )

    results.sort(key=lambda x: float(x.get("final_price", 0)))  # type: ignore[arg-type]

    return results


def _execute_purchase(offer: Offer, dealership_match: Dict[str, Any]) -> Optional[Sale]:
    """
    Execute the purchase transaction for a matched offer.

    Updates: Sale, Customer balance/stats, Dealership balance/stats, Inventory quantity.

    Args:
        offer: Offer being fulfilled.
        dealership_match: Selected dealership match details.

    Returns:
        Created Sale instance or None if failed.
    """
    try:
        with transaction.atomic():
            dealership = Dealership.objects.select_for_update().get(id=dealership_match["dealership_id"])
            inventory = DealershipInventory.objects.select_for_update().get(id=dealership_match["inventory_id"])
            customer = offer.customer

            if inventory.quantity < 1:
                return None

            final_price = Decimal(str(dealership_match["final_price"]))

            if customer.balance < final_price:
                return None

            sale = Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=offer.car_model,
                price=final_price,
                original_price=Decimal(str(dealership_match["base_price"])),
                discount_applied=Decimal(str(dealership_match["discount_percent"])),
                promotion_applied_id=dealership_match.get("promotion_id"),
                offer=offer,
            )

            customer.balance -= final_price
            customer.total_purchases += 1
            customer.total_spent += final_price
            customer.save(update_fields=["balance", "total_purchases", "total_spent", "updated_at"])

            dealership.balance += final_price
            dealership.total_sales += 1
            dealership.total_revenue += final_price

            profit = final_price - inventory.purchase_price
            dealership.total_profit += profit
            dealership.save(update_fields=["balance", "total_sales", "total_revenue", "total_profit", "updated_at"])

            inventory.quantity -= 1
            inventory.times_sold += 1
            inventory.last_sale_date = timezone.now()
            inventory.save(update_fields=["quantity", "times_sold", "last_sale_date", "updated_at"])

            return sale

    except Exception:
        return None
