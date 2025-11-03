from rest_framework import serializers
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from cars.serializers import CarModelListSerializer


class SupplierSerializer(serializers.ModelSerializer):

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

