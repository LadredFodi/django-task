from rest_framework import serializers
from django.contrib.auth.models import User
from customers.models import Customer, Sale
from cars.serializers import CarModelListSerializer
from customers.services import CustomerService


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class CustomerSerializer(serializers.ModelSerializer):

    user_details = UserSerializer(source='user', read_only=True)
    country_name = serializers.CharField(source='country.name', read_only=True)
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'user',
            'user_details',
            'phone',
            'date_of_birth',
            'country',
            'country_name',
            'city',
            'address',
            'balance',
            'email_verified',
            'total_purchases',
            'total_spent',
            'customer_type',
            'customer_type_display',
            'loyalty_points',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'user', 'total_purchases', 'total_spent', 
            'loyalty_points', 'created_at', 'updated_at'
        ]


class CustomerListSerializer(serializers.ModelSerializer):

    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    customer_type_display = serializers.CharField(source='get_customer_type_display', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id',
            'user',
            'username',
            'email',
            'customer_type',
            'customer_type_display',
            'total_purchases',
            'total_spent',
            'loyalty_points',
            'is_active',
        ]


class SaleSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source='dealership.name', read_only=True)
    customer_username = serializers.CharField(source='customer.user.username', read_only=True)
    car_model_detail = CarModelListSerializer(source='car_model', read_only=True)
    promotion_name = serializers.CharField(source='promotion_applied.name', read_only=True)
    offer_id = serializers.IntegerField(source='offer.id', read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id',
            'dealership',
            'dealership_name',
            'customer',
            'customer_username',
            'car_model',
            'car_model_detail',
            'price',
            'original_price',
            'discount_applied',
            'promotion_applied',
            'promotion_name',
            'offer',
            'offer_id',
            'vin_number',
            'notes',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):

        price = data.get('price')
        original_price = data.get('original_price')
        discount_applied = data.get('discount_applied', 0)
        
        if price and original_price and price > original_price:
            raise serializers.ValidationError(
                "Sale price cannot be higher than the original price."
            )
        
        if price and original_price and discount_applied:
            expected_price = original_price * (1 - discount_applied / 100)
            if abs(float(price) - float(expected_price)) > 0.01:
                raise serializers.ValidationError(
                    "Price does not match the applied discount."
                )
        
        return data


class SaleListSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source='dealership.name', read_only=True)
    customer_username = serializers.CharField(source='customer.user.username', read_only=True)
    car_brand = serializers.CharField(source='car_model.brand', read_only=True)
    car_model_name = serializers.CharField(source='car_model.model', read_only=True)
    car_year = serializers.IntegerField(source='car_model.year', read_only=True)
    
    class Meta:
        model = Sale
        fields = [
            'id',
            'dealership',
            'dealership_name',
            'customer',
            'customer_username',
            'car_model',
            'car_brand',
            'car_model_name',
            'car_year',
            'price',
            'vin_number',
            'created_at',
        ]


class CustomerRegistrationSerializer(serializers.ModelSerializer):

    username = serializers.CharField(write_only=True)
    email = serializers.EmailField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = Customer
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name',
            'phone', 'date_of_birth', 'country', 'city', 'address'
        ]
    
    def validate(self, data):

        if data.get('password') != data.get('password_confirm'):
            raise serializers.ValidationError("Passwords do not match.")
        
        if User.objects.filter(username=data.get('username')).exists():
            raise serializers.ValidationError("User with this username already exists.")
        
        if User.objects.filter(email=data.get('email')).exists():
            raise serializers.ValidationError("User with this email already exists.")
        
        return data
    
    def create(self, validated_data):
        username = validated_data.pop('username')
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        first_name = validated_data.pop('first_name', '')
        last_name = validated_data.pop('last_name', '')
        
        customer = CustomerService.register_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **validated_data
        )
        
        return customer

