from decimal import Decimal
from typing import Any, Optional

from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q, QuerySet, Sum

from customers.models import Customer, Sale
from dealerships.models import DealershipInventory
from dealerships.services import DealershipInventoryService


class CustomerService:

    @staticmethod
    def get_all_active_customers() -> QuerySet[Customer]:
        return Customer.objects.select_related("user").filter(is_active=True)

    @staticmethod
    def get_customer_by_id(customer_id: int) -> Optional[Customer]:
        try:
            return Customer.objects.select_related("user").get(id=customer_id, is_active=True)
        except Customer.DoesNotExist:
            return None

    @staticmethod
    def get_customer_by_user(user: User) -> Optional[Customer]:
        try:
            return user.customer_profile
        except Customer.DoesNotExist:
            return None

    @staticmethod
    def get_by_user(user: User) -> Optional[Customer]:
        return CustomerService.get_customer_by_user(user)

    @staticmethod
    def create_customer(user: User, **kwargs: Any) -> Customer:
        return Customer.objects.create(user=user, **kwargs)

    @staticmethod
    def update_customer(customer: Customer, data: dict[str, Any]) -> Customer:
        for key, value in data.items():
            setattr(customer, key, value)
        customer.save()
        return customer

    @staticmethod
    def update_balance(customer: Customer, amount: Decimal) -> Customer:
        customer.balance += amount
        customer.save(update_fields=["balance", "updated_at"])
        return customer

    @staticmethod
    def verify_email(customer: Customer) -> Customer:
        customer.email_verified = True
        customer.save(update_fields=["email_verified", "updated_at"])
        return customer

    @staticmethod
    def get_statistics(customer: Customer) -> dict:
        purchases_stats = customer.purchases.filter(is_active=True).aggregate(
            total_count=Count("id"),
            total_spent=Sum("price"),
            avg_price=Avg("price"),
            avg_discount=Avg("discount_applied"),
        )

        favorite_brands = list(
            customer.purchases.filter(is_active=True)
            .values("car_model__brand")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        favorite_dealerships = list(
            customer.purchases.filter(is_active=True)
            .values("dealership__name", "dealership__city")
            .annotate(purchases_count=Count("id"), total_spent=Sum("price"))
            .order_by("-purchases_count")[:5]
        )

        recent_purchases = list(
            customer.purchases.filter(is_active=True)
            .select_related("car_model", "dealership")
            .values(
                "id",
                "car_model__brand",
                "car_model__model",
                "car_model__year",
                "dealership__name",
                "price",
                "created_at",
            )
            .order_by("-created_at")[:10]
        )

        return {
            "customer_id": customer.id,
            "username": customer.user.username,
            "email": customer.user.email,
            "customer_type": customer.customer_type,
            "total_purchases": customer.total_purchases,
            "total_spent": float(customer.total_spent),
            "balance": float(customer.balance),
            "loyalty_points": customer.loyalty_points,
            "purchases": {
                "count": purchases_stats["total_count"] or 0,
                "total": float(purchases_stats["total_spent"] or 0),
                "average": float(purchases_stats["avg_price"] or 0),
                "avg_discount": float(purchases_stats["avg_discount"] or 0),
            },
            "favorite_brands": favorite_brands,
            "favorite_dealerships": favorite_dealerships,
            "recent_purchases": recent_purchases,
        }

    @staticmethod
    def get_vip_customers() -> QuerySet[Customer]:
        return Customer.objects.filter(Q(customer_type="vip") | Q(customer_type="premium"), is_active=True).order_by(
            "-total_spent"
        )

    @staticmethod
    def register_user(username: str, email: str, password: str, **kwargs: Any) -> Customer:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=kwargs.pop("first_name", ""),
            last_name=kwargs.pop("last_name", ""),
        )

        customer = Customer.objects.create(user=user, **kwargs)
        return customer


class SaleService:

    @staticmethod
    def get_all_active_sales() -> QuerySet[Sale]:
        return Sale.objects.select_related("dealership", "customer", "car_model").filter(is_active=True)

    @staticmethod
    def get_sales_by_customer(customer: Customer) -> QuerySet[Sale]:
        return (
            Sale.objects.filter(customer=customer, is_active=True)
            .select_related("dealership", "car_model")
            .order_by("-created_at")
        )

    @staticmethod
    def get_sales_by_dealership(dealership_id: int) -> QuerySet[Sale]:
        return (
            Sale.objects.filter(dealership_id=dealership_id, is_active=True)
            .select_related("customer", "car_model")
            .order_by("-created_at")
        )

    @staticmethod
    def create_sale(data: dict[str, Any]) -> Sale:
        sale = Sale.objects.create(**data)

        customer = sale.customer
        customer.total_purchases += 1
        customer.total_spent += sale.price
        customer.balance -= sale.price
        customer.save(update_fields=["total_purchases", "total_spent", "balance", "updated_at"])

        dealership = sale.dealership
        dealership.total_sales += 1
        dealership.total_revenue += sale.price
        dealership.balance += sale.price
        dealership.save(update_fields=["total_sales", "total_revenue", "balance", "updated_at"])

        try:
            inventory = DealershipInventory.objects.get(
                dealership=sale.dealership, car_model=sale.car_model, is_active=True
            )
            DealershipInventoryService.decrease_quantity(inventory, 1)
        except DealershipInventory.DoesNotExist:
            pass

        return sale

    @staticmethod
    def get_sales_statistics() -> dict:
        queryset = Sale.objects.filter(is_active=True)

        stats = queryset.aggregate(
            total_sales=Count("id"),
            total_revenue=Sum("price"),
            avg_price=Avg("price"),
            avg_discount=Avg("discount_applied"),
            sum_original=Sum("original_price"),
            sum_price=Sum("price"),
        )

        total_discount_given = 0
        if stats["sum_original"] and stats["sum_price"]:
            total_discount_given = stats["sum_original"] - stats["sum_price"]

        sales_by_dealership = list(
            queryset.values("dealership__name", "dealership__city")
            .annotate(count=Count("id"), revenue=Sum("price"))
            .order_by("-revenue")[:10]
        )

        top_models = list(
            queryset.values("car_model__brand", "car_model__model", "car_model__year")
            .annotate(count=Count("id"), revenue=Sum("price"))
            .order_by("-count")[:10]
        )

        promo_queryset = queryset.filter(promotion_applied__isnull=False)
        promotions_impact = promo_queryset.aggregate(
            sales_with_promotion=Count("id"),
            sum_original_promo=Sum("original_price"),
            sum_price_promo=Sum("price"),
            avg_promotion_discount=Avg("discount_applied"),
        )

        promo_discount = 0
        if promotions_impact["sum_original_promo"] and promotions_impact["sum_price_promo"]:
            promo_discount = promotions_impact["sum_original_promo"] - promotions_impact["sum_price_promo"]

        return {
            "overall": {
                "total_sales": stats["total_sales"] or 0,
                "total_revenue": float(stats["total_revenue"] or 0),
                "avg_price": float(stats["avg_price"] or 0),
                "avg_discount": float(stats["avg_discount"] or 0),
                "total_discount_given": float(total_discount_given),
            },
            "top_dealerships": sales_by_dealership,
            "top_models": top_models,
            "promotions_impact": {
                "sales_with_promotion": promotions_impact["sales_with_promotion"] or 0,
                "total_discount": float(promo_discount),
                "avg_promotion_discount": float(promotions_impact["avg_promotion_discount"] or 0),
            },
        }
