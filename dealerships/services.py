"""Service layer for dealership operations and business logic."""

from decimal import Decimal
from typing import Any, Optional

from django.contrib.gis.db.models.functions import Distance as DistanceFunction
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.db.models import Avg, Count, QuerySet, Sum
from django.utils import timezone

from dealerships.models import Dealership, DealershipInventory, DealershipPreference, Purchase


class DealershipService:
    """Service class for dealership management operations."""

    @staticmethod
    def get_all_active_dealerships() -> QuerySet[Dealership]:
        """Get all active dealerships."""
        return Dealership.objects.filter(is_active=True)

    @staticmethod
    def get_dealership_by_id(dealership_id: int) -> Optional[Dealership]:
        """Get dealership by ID."""
        try:
            return Dealership.objects.get(id=dealership_id, is_active=True)
        except Dealership.DoesNotExist:
            return None

    @staticmethod
    def create_dealership(data: dict[str, Any]) -> Dealership:
        """Create new dealership."""
        return Dealership.objects.create(**data)

    @staticmethod
    def update_dealership(dealership: Dealership, data: dict[str, Any]) -> Dealership:
        """Update dealership with provided data."""
        for key, value in data.items():
            setattr(dealership, key, value)
        dealership.save()
        return dealership

    @staticmethod
    def update_balance(dealership: Dealership, amount: Decimal) -> Dealership:
        """Update dealership balance (add or subtract amount)."""
        dealership.balance += amount
        dealership.save(update_fields=["balance", "updated_at"])
        return dealership

    @staticmethod
    def get_dealership_statistics(dealership: Dealership) -> dict:
        """Get comprehensive statistics for a dealership."""
        inventory_stats = dealership.inventory.filter(is_active=True).aggregate(
            total_cars=Sum("quantity"),
            total_models=Count("id"),
            avg_selling_price=Avg("selling_price"),
            avg_purchase_price=Avg("purchase_price"),
        )

        sales_stats = dealership.sales.filter(is_active=True).aggregate(
            total_sales_count=Count("id"),
            total_sales_revenue=Sum("price"),
            avg_sale_price=Avg("price"),
            avg_discount=Avg("discount_applied"),
        )

        unique_customers = dealership.sales.filter(is_active=True).values("customer").distinct().count()

        purchases_stats = dealership.purchases.filter(is_active=True).aggregate(
            total_purchases_count=Count("id"),
            total_purchases_amount=Sum("total_price"),
            avg_purchase_price=Avg("unit_price"),
        )

        top_selling_models = list(
            dealership.sales.filter(is_active=True)
            .values("car_model__brand", "car_model__model", "car_model__year")
            .annotate(count=Count("id"), revenue=Sum("price"))
            .order_by("-count")[:5]
        )

        top_customers = list(
            dealership.sales.filter(is_active=True)
            .values("customer__user__username", "customer__user__email")
            .annotate(purchases_count=Count("id"), total_spent=Sum("price"))
            .order_by("-total_spent")[:10]
        )

        now = timezone.now()
        active_promotions = list(
            dealership.promotions.filter(
                is_active=True, promotion__is_active=True, promotion__start_date__lte=now, promotion__end_date__gte=now
            )
            .values("promotion__name", "discount_percent", "times_applied")
            .order_by("-discount_percent")[:10]
        )

        return {
            "balance": float(dealership.balance),
            "total_sales": dealership.total_sales,
            "total_revenue": float(dealership.total_revenue),
            "total_profit": float(dealership.total_profit),
            "inventory": {
                "total_cars": inventory_stats["total_cars"] or 0,
                "total_models": inventory_stats["total_models"] or 0,
                "avg_selling_price": float(inventory_stats["avg_selling_price"] or 0),
                "avg_purchase_price": float(inventory_stats["avg_purchase_price"] or 0),
            },
            "sales": {
                "total_count": sales_stats["total_sales_count"] or 0,
                "total_revenue": float(sales_stats["total_sales_revenue"] or 0),
                "avg_price": float(sales_stats["avg_sale_price"] or 0),
                "avg_discount": float(sales_stats["avg_discount"] or 0),
                "unique_customers": unique_customers,
            },
            "purchases": {
                "total_count": purchases_stats["total_purchases_count"] or 0,
                "total_amount": float(purchases_stats["total_purchases_amount"] or 0),
                "avg_price": float(purchases_stats["avg_purchase_price"] or 0),
            },
            "top_selling_models": top_selling_models,
            "top_customers": top_customers,
            "active_promotions": active_promotions,
        }

    @staticmethod
    def find_nearby(latitude: float, longitude: float, radius: float = 50) -> QuerySet[Dealership]:
        """Find dealerships within specified radius using PostGIS."""
        point = Point(longitude, latitude, srid=4326)
        return (
            Dealership.objects.filter(is_active=True, location__distance_lte=(point, Distance(km=radius)))
            .annotate(distance=DistanceFunction("location", point))
            .order_by("distance")
        )


class DealershipInventoryService:
    """Service class for dealership inventory management."""

    @staticmethod
    def get_all_active_inventory() -> QuerySet[DealershipInventory]:
        """Get all active inventory items."""
        return DealershipInventory.objects.select_related("dealership", "car_model").filter(
            is_active=True, dealership__is_active=True
        )

    @staticmethod
    def get_inventory_by_dealership(dealership_id: int) -> QuerySet[DealershipInventory]:
        """Get inventory for specific dealership."""
        return DealershipInventory.objects.filter(dealership_id=dealership_id, is_active=True).select_related(
            "car_model"
        )

    @staticmethod
    def get_available_inventory() -> QuerySet[DealershipInventory]:
        """Get inventory items with quantity > 0."""
        return DealershipInventory.objects.filter(is_active=True, quantity__gt=0).select_related(
            "dealership", "car_model"
        )

    @staticmethod
    def get_popular_inventory(limit: int = 20) -> QuerySet[DealershipInventory]:
        """Get most popular inventory items by sales count."""
        return (
            DealershipInventory.objects.filter(is_active=True, times_sold__gt=0)
            .select_related("dealership", "car_model")
            .order_by("-times_sold")[:limit]
        )

    @staticmethod
    def create_inventory_item(data: dict[str, Any]) -> DealershipInventory:
        """Create new inventory item."""
        return DealershipInventory.objects.create(**data)

    @staticmethod
    def update_inventory_item(inventory: DealershipInventory, data: dict) -> DealershipInventory:
        """Update inventory item with provided data."""
        for key, value in data.items():
            setattr(inventory, key, value)
        inventory.save()
        return inventory

    @staticmethod
    def decrease_quantity(inventory: DealershipInventory, amount: int = 1) -> DealershipInventory:
        """Decrease inventory quantity (for sales)."""
        if inventory.quantity >= amount:
            inventory.quantity -= amount
            inventory.times_sold += 1
            inventory.save(update_fields=["quantity", "times_sold", "updated_at"])
        return inventory

    @staticmethod
    def increase_quantity(inventory: DealershipInventory, amount: int) -> DealershipInventory:
        """Increase inventory quantity (for purchases)."""
        inventory.quantity += amount
        inventory.save(update_fields=["quantity", "updated_at"])
        return inventory


class PurchaseService:
    """Service class for purchase management operations."""

    @staticmethod
    def get_all_active_purchases() -> QuerySet[Purchase]:
        """Get all active purchases."""
        return Purchase.objects.select_related("dealership", "supplier", "car_model").filter(is_active=True)

    @staticmethod
    def get_purchases_by_dealership(dealership_id: int) -> QuerySet[Purchase]:
        """Get all purchases for specific dealership."""
        return (
            Purchase.objects.filter(dealership_id=dealership_id, is_active=True)
            .select_related("supplier", "car_model")
            .order_by("-created_at")
        )

    @staticmethod
    def create_purchase(data: dict[str, Any]) -> Purchase:
        """Create purchase and update inventory and balance."""
        purchase = Purchase.objects.create(**data)

        inventory, created = DealershipInventory.objects.get_or_create(
            dealership=purchase.dealership,
            car_model=purchase.car_model,
            defaults={
                "quantity": purchase.quantity,
                "purchase_price": purchase.unit_price,
                "selling_price": purchase.unit_price * Decimal("1.2"),
            },
        )

        if not created:
            total_cost = (inventory.purchase_price * inventory.quantity) + purchase.total_price
            new_quantity = inventory.quantity + purchase.quantity
            inventory.purchase_price = total_cost / new_quantity
            inventory.quantity = new_quantity
            inventory.save()

        purchase.dealership.balance -= purchase.total_price
        purchase.dealership.save(update_fields=["balance", "updated_at"])

        return purchase

    @staticmethod
    def get_purchase_count(supplier_id: int, dealership_id: int) -> int:
        """Count purchases between specific supplier and dealership."""
        return Purchase.objects.filter(supplier_id=supplier_id, dealership_id=dealership_id, is_active=True).count()

    @staticmethod
    def get_statistics() -> dict[str, Any]:
        """Get comprehensive purchase statistics."""
        queryset = Purchase.objects.filter(is_active=True)

        basic_stats = queryset.aggregate(
            total_purchases=Count("id"),
            total_quantity=Sum("quantity"),
            total_amount=Sum("total_price"),
            avg_unit_price=Avg("unit_price"),
        )

        top_suppliers = list(
            queryset.values("supplier__name")
            .annotate(purchases_count=Count("id"), total_quantity=Sum("quantity"), total_revenue=Sum("total_price"))
            .order_by("-total_revenue")[:10]
        )

        top_car_models = list(
            queryset.values("car_model__brand", "car_model__model")
            .annotate(purchases_count=Count("id"), total_quantity=Sum("quantity"))
            .order_by("-total_quantity")[:10]
        )

        return {
            "total_purchases": basic_stats["total_purchases"] or 0,
            "total_quantity": basic_stats["total_quantity"] or 0,
            "total_amount": float(basic_stats["total_amount"] or 0),
            "avg_unit_price": float(basic_stats["avg_unit_price"] or 0),
            "top_suppliers": top_suppliers,
            "top_car_models": top_car_models,
        }


class DealershipPreferenceService:
    """Service class for dealership preference management."""

    @staticmethod
    def get_preference_by_dealership(dealership_id: int) -> Optional[DealershipPreference]:
        """Get preferences for specific dealership."""
        try:
            return DealershipPreference.objects.get(dealership_id=dealership_id, is_active=True)
        except DealershipPreference.DoesNotExist:
            return None

    @staticmethod
    def create_preference(data: dict[str, Any]) -> DealershipPreference:
        """Create new dealership preference."""
        return DealershipPreference.objects.create(**data)

    @staticmethod
    def update_preference(preference: DealershipPreference, data: dict[str, Any]) -> DealershipPreference:
        """Update dealership preference with provided data."""
        for key, value in data.items():
            setattr(preference, key, value)
        preference.save()
        return preference
