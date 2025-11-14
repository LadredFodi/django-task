import pytest
from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.utils import timezone
from django.db import connection
from datetime import timedelta
from faker import Faker
from rest_framework.test import APIClient

from django.apps import apps
from cars.models import CarModel
from customers.models import Customer, Sale
from dealerships.models import Dealership, DealershipInventory, DealershipPreference, Purchase
from suppliers.models import Supplier, SupplierCar, SupplierDiscount
from promotions.models import Promotion, PromotionDealership, PromotionSupplier
from offers.models import Offer

fake = Faker()

@pytest.fixture
def api_client():
    return APIClient()



@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='adminpass123'
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        username='user',
        email='user@test.com',
        password='userpass123',
        first_name='John',
        last_name='Doe'
    )


@pytest.fixture
def user_factory(db):
    def create_user(**kwargs):
        defaults = {
            'username': fake.user_name(),
            'email': fake.email(),
            'password': 'testpass123',
            'first_name': fake.first_name(),
            'last_name': fake.last_name(),
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        return user
    return create_user



@pytest.fixture
def car_model(db):
    return CarModel.objects.create(
        brand='Toyota',
        model='Camry',
        year=2023,
        body_type='sedan',
        color='black',
        fuel_type='gasoline',
        engine_volume=Decimal('2.5'),
        horsepower=203,
        transmission='automatic',
        drive_type='fwd',
        description='Reliable sedan'
    )


@pytest.fixture
def car_model_factory(db):
    def create_car(**kwargs):
        defaults = {
            'brand': fake.company(),
            'model': fake.word().capitalize(),
            'year': fake.random_int(min=2020, max=2024),
            'body_type': fake.random_element(['sedan', 'suv', 'hatchback']),
            'color': fake.color_name(),
            'fuel_type': fake.random_element(['gasoline', 'diesel', 'electric']),
            'engine_volume': Decimal(str(fake.random_int(min=15, max=50) / 10)),
            'horsepower': fake.random_int(min=100, max=400),
            'transmission': fake.random_element(['manual', 'automatic']),
            'drive_type': fake.random_element(['fwd', 'rwd', 'awd']),
        }
        defaults.update(kwargs)
        return CarModel.objects.create(**defaults)
    return create_car



@pytest.fixture
def customer(db, regular_user):
    return Customer.objects.create(
        user=regular_user,
        phone='+1234567890',
        country='US',
        city='New York',
        address='123 Main St',
        balance=Decimal('50000.00'),
        email_verified=True,
        customer_type='regular'
    )


@pytest.fixture
def customer_factory(db, user_factory):
    def create_customer(**kwargs):
        user = kwargs.pop('user', None)
        if not user:
            user = user_factory()
        
        defaults = {
            'user': user,
            'phone': fake.phone_number(),
            'country': fake.country_code(),
            'city': fake.city(),
            'address': fake.address(),
            'balance': Decimal(str(fake.random_int(min=10000, max=100000))),
            'email_verified': True,
            'customer_type': 'regular',
        }
        defaults.update(kwargs)
        return Customer.objects.create(**defaults)
    return create_customer



@pytest.fixture
def dealership(db):
    return Dealership.objects.create(
        name='Best Cars Dealership',
        country='US',
        city='Los Angeles',
        address='456 Auto Street',
        email='bestcars@test.com',
        phone='+1987654321',
        balance=Decimal('100000.00'),
        location=Point(-118.2437, 34.0522, srid=4326)
    )


@pytest.fixture
def dealership_factory(db):
    def create_dealership(**kwargs):
        defaults = {
            'name': f"{fake.company()} Dealership",
            'country': fake.country_code(),
            'city': fake.city(),
            'address': fake.address(),
            'email': fake.email(),
            'phone': fake.phone_number(),
            'balance': Decimal(str(fake.random_int(min=50000, max=500000))),
        }
        if 'location' not in kwargs:
            lon = float(fake.longitude())
            lat = float(fake.latitude())
            defaults['location'] = Point(lon, lat, srid=4326)
        
        defaults.update(kwargs)
        return Dealership.objects.create(**defaults)
    return create_dealership


@pytest.fixture
def dealership_inventory(db, dealership, car_model):
    return DealershipInventory.objects.create(
        dealership=dealership,
        car_model=car_model,
        quantity=10,
        purchase_price=Decimal('25000.00'),
        selling_price=Decimal('30000.00')
    )


@pytest.fixture
def dealership_preference(db, dealership):          
    return DealershipPreference.objects.create(
        dealership=dealership,
        preferred_brands=['Toyota', 'Honda'],
        preferred_body_types=['sedan', 'suv'],
        preferred_fuel_types=['gasoline', 'hybrid'],
        min_price=Decimal('20000.00'),
        max_price=Decimal('50000.00')
    )


@pytest.fixture
def supplier(db):
    return Supplier.objects.create(
        name='Global Auto Supplier',
        country='DE',
        founded_year=2000,
        email='supplier@test.com',
        phone='+49123456789',
        rating=Decimal('7.5')
    )


@pytest.fixture
def supplier_factory(db):
    def create_supplier(**kwargs):
        defaults = {
            'name': f"{fake.company()} Supplier",
            'country': fake.country_code(),
            'founded_year': fake.random_int(min=1990, max=2020),
            'email': fake.email(),
            'phone': fake.phone_number(),
            'rating': Decimal(str(fake.random_int(min=50, max=80) / 10)),
        }
        defaults.update(kwargs)
        return Supplier.objects.create(**defaults)
    return create_supplier


@pytest.fixture
def supplier_car(db, supplier, car_model):
    return SupplierCar.objects.create(
        supplier=supplier,
        car_model=car_model,
        price=Decimal('23000.00'),
        available_quantity=50,
        delivery_days=10,
        min_order_quantity=1
    )


@pytest.fixture
def supplier_discount(db, supplier, dealership):
    return SupplierDiscount.objects.create(
        supplier=supplier,
        dealership=dealership,
        discount_percent=Decimal('5.00'),
        min_purchases=10,
        is_applied=False
    )


@pytest.fixture
def promotion(db):
    now = timezone.now()
    return Promotion.objects.create(
        name='Summer Sale',
        description='Big summer discounts',
        promotion_type='seasonal',
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=30),
        default_discount_percent=Decimal('15.00')
    )


@pytest.fixture
def promotion_dealership(db, promotion, dealership):
    return PromotionDealership.objects.create(
        promotion=promotion,
        dealership=dealership,
        discount_percent=Decimal('15.00')
    )


@pytest.fixture
def promotion_supplier(db, promotion, supplier):
    return PromotionSupplier.objects.create(
        promotion=promotion,
        supplier=supplier,
        discount_percent=Decimal('10.00')
    )


@pytest.fixture
def sale(db, dealership, customer, car_model):
    return Sale.objects.create(
        dealership=dealership,
        customer=customer,
        car_model=car_model,
        price=Decimal('28500.00'),
        original_price=Decimal('30000.00'),
        discount_applied=Decimal('5.00')
    )


@pytest.fixture
def purchase(db, dealership, supplier, car_model):
    return Purchase.objects.create(
        dealership=dealership,
        supplier=supplier,
        car_model=car_model,
        quantity=5,
        unit_price=Decimal('23000.00'),
        total_price=Decimal('115000.00')
    )


@pytest.fixture
def offer(db, customer, car_model):
    return Offer.objects.create(
        customer=customer,
        car_model=car_model,
        max_price=Decimal('35000.00'),
        status='pending'
    )


@pytest.fixture
def authenticated_client(api_client, regular_user):
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client

