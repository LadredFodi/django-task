"""Serializers for supplier and catalog models."""

from rest_framework import serializers
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from cars.serializers import CarModelListSerializer


class SupplierSerializer(serializers.ModelSerializer):
    """Detailed serializer for Supplier with annotated car count."""

    country_name = serializers.CharField(source='country.name', read_only=True)
    total_cars = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'country',
            'country_name',
            'founded_year',
            'email',
            'phone',
            'website',
            'description',
            'rating',
            'total_sales',
            'total_revenue',
            'total_cars',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'total_sales', 'total_revenue', 'created_at', 'updated_at']


class SupplierListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Supplier list views."""

    country_name = serializers.CharField(source='country.name', read_only=True)
    
    class Meta:
        model = Supplier
        fields = [
            'id',
            'name',
            'country',
            'country_name',
            'rating',
            'total_sales',
            'is_active',
        ]
        read_only_fields = ['id']


class SupplierCarSerializer(serializers.ModelSerializer):
    """Detailed serializer for SupplierCar with related car model details."""

    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    car_model_detail = CarModelListSerializer(source='car_model', read_only=True)
    
    class Meta:
        model = SupplierCar
        fields = [
            'id',
            'supplier',
            'supplier_name',
            'car_model',
            'car_model_detail',
            'price',
            'available_quantity',
            'delivery_days',
            'min_order_quantity',
            'times_sold',
            'last_purchase_date',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'times_sold', 'last_purchase_date', 'created_at', 'updated_at']


class SupplierCarListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for SupplierCar list views."""

    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    car_brand = serializers.CharField(source='car_model.brand', read_only=True)
    car_model_name = serializers.CharField(source='car_model.model', read_only=True)
    car_year = serializers.IntegerField(source='car_model.year', read_only=True)
    
    class Meta:
        model = SupplierCar
        fields = [
            'id',
            'supplier',
            'supplier_name',
            'car_model',
            'car_brand',
            'car_model_name',
            'car_year',
            'price',
            'available_quantity',
            'delivery_days',
            'is_active',
        ]


class SupplierDiscountSerializer(serializers.ModelSerializer):
    """Serializer for SupplierDiscount with related names."""

    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    dealership_name = serializers.CharField(source='dealership.name', read_only=True)
    
    class Meta:
        model = SupplierDiscount
        fields = [
            'id',
            'supplier',
            'supplier_name',
            'dealership',
            'dealership_name',
            'discount_percent',
            'min_purchases',
            'is_applied',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'is_applied', 'created_at', 'updated_at']


class SupplierStatisticsSerializer(serializers.Serializer):
    """Serializer for supplier statistics and analytics."""

    supplier_id = serializers.IntegerField()
    supplier_name = serializers.CharField()
    rating = serializers.DecimalField(max_digits=4, decimal_places=2)
    
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    avg_order_value = serializers.DecimalField(max_digits=16, decimal_places=2)
  
    total_car_models = serializers.IntegerField()
    total_available_cars = serializers.IntegerField()
    average_price = serializers.DecimalField(max_digits=16, decimal_places=2)
    
    partner_dealerships = serializers.IntegerField()
    active_discounts = serializers.IntegerField()
    
    top_partner_dealerships = serializers.ListField(child=serializers.DictField())
    
    top_selling_models = serializers.ListField(child=serializers.DictField())
    
    active_promotions = serializers.ListField(child=serializers.DictField())

