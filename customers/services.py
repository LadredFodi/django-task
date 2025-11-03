from django.db.models import Count, Sum, Avg, Q
from django.contrib.auth.models import User
from typing import Optional, Any, QuerySet
from decimal import Decimal
from customers.models import Customer, Sale


class CustomerService:
    
    @staticmethod
    def get_all_active_customers() -> QuerySet[Customer]:
        return Customer.objects.select_related('user').filter(is_active=True)
    
    @staticmethod
    def get_customer_by_id(customer_id: int) -> Optional[Customer]:
        try:
            return Customer.objects.select_related('user').get(
                id=customer_id,
                is_active=True
            )
        except Customer.DoesNotExist:
            return None
    
    @staticmethod
    def get_customer_by_user(user: User) -> Optional[Customer]:
        try:
            return user.customer_profile
        except Customer.DoesNotExist:
            return None
    
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
        customer.save(update_fields=['balance', 'updated_at'])
        return customer
    
    @staticmethod
    def verify_email(customer: Customer) -> Customer:
        customer.email_verified = True
        customer.save(update_fields=['email_verified', 'updated_at'])
        return customer
    
    @staticmethod
    def get_statistics(customer: Customer) -> dict:
        purchases_stats = customer.purchases.filter(is_active=True).aggregate(
            total_count=Count('id'),
            total_spent=Sum('price'),
            avg_price=Avg('price'),
        )
        
        favorite_brands = list(
            customer.purchases.filter(is_active=True)
            .values('car_model__brand')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )
        
        return {
            'total_purchases': customer.total_purchases,
            'total_spent': float(customer.total_spent),
            'balance': float(customer.balance),
            'loyalty_points': customer.loyalty_points,
            'customer_type': customer.customer_type,
            'purchases': {
                'count': purchases_stats['total_count'] or 0,
                'total': float(purchases_stats['total_spent'] or 0),
                'average': float(purchases_stats['avg_price'] or 0),
            },
            'favorite_brands': favorite_brands,
        }
    
    @staticmethod
    def get_vip_customers() -> QuerySet[Customer]:
        return Customer.objects.filter(
            Q(customer_type='vip') | Q(customer_type='premium'),
            is_active=True
        ).order_by('-total_spent')
    
    @staticmethod
    def register_user(username: str, email: str, password: str, **kwargs: Any) -> Customer:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=kwargs.pop('first_name', ''),
            last_name=kwargs.pop('last_name', '')
        )
        
        customer = Customer.objects.create(user=user, **kwargs)
        return customer


class SaleService:
    
    @staticmethod
    def get_all_active_sales() -> QuerySet[Sale]:
        return Sale.objects.select_related('dealership', 'customer', 'car_model').filter(
            is_active=True
        )
    
    @staticmethod
    def get_sales_by_customer(customer: Customer) -> QuerySet[Sale]:
        return Sale.objects.filter(
            customer=customer,
            is_active=True
        ).select_related('dealership', 'car_model').order_by('-created_at')
    
    @staticmethod
    def get_sales_by_dealership(dealership_id: int) -> QuerySet[Sale]:
        return Sale.objects.filter(
            dealership_id=dealership_id,
            is_active=True
        ).select_related('customer', 'car_model').order_by('-created_at')
    
    @staticmethod
    def create_sale(data: dict[str, Any]) -> Sale:
        sale = Sale.objects.create(**data)
        
        customer = sale.customer
        customer.total_purchases += 1
        customer.total_spent += sale.price
        customer.balance -= sale.price
        customer.save(update_fields=['total_purchases', 'total_spent', 'balance', 'updated_at'])
        
        dealership = sale.dealership
        dealership.total_sales += 1
        dealership.total_revenue += sale.price
        dealership.balance += sale.price
        dealership.save(update_fields=['total_sales', 'total_revenue', 'balance', 'updated_at'])
    
        from dealerships.services import DealershipInventoryService
        from dealerships.models import DealershipInventory
        
        try:
            inventory = DealershipInventory.objects.get(
                dealership=sale.dealership,
                car_model=sale.car_model,
                is_active=True
            )
            DealershipInventoryService.decrease_quantity(inventory, 1)
        except DealershipInventory.DoesNotExist:
            pass
        
        return sale
    
    @staticmethod
    def get_sales_statistics() -> dict:
        queryset = Sale.objects.filter(is_active=True)
        
        stats = queryset.aggregate(
            total_sales=Count('id'),
            total_revenue=Sum('price'),
            avg_price=Avg('price'),
            avg_discount=Avg('discount_applied'),
        )
        
        sales_by_dealership = list(
            queryset.values('dealership__name')
            .annotate(count=Count('id'), revenue=Sum('price'))
            .order_by('-revenue')[:10]
        )
        
        top_models = list(
            queryset.values('car_model__brand', 'car_model__model')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        
        return {
            'overall': stats,
            'top_dealerships': sales_by_dealership,
            'top_models': top_models,
        }

