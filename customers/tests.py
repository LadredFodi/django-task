import pytest
from decimal import Decimal
from django.urls import reverse
from rest_framework import status

from customers.models import Customer, Sale
from customers.services import CustomerService, SaleService


@pytest.mark.django_db
class TestCustomerModel:
    
    def test_create_customer(self, customer):
        assert customer.pk is not None
        assert customer.user.username == 'user'
        assert customer.balance == Decimal('50000.00')
        assert customer.is_active is True
    
    def test_customer_str(self, customer):
        expected = f"{customer.user.username} ({customer.user.email})"
        assert str(customer) == expected
    
    def test_customer_one_to_one_with_user(self, regular_user, db):
        customer = Customer.objects.create(
            user=regular_user,
            balance=Decimal('10000.00')
        )
        
        assert regular_user.customer_profile == customer
    
    def test_customer_balance_validator(self, customer):
        customer.balance = Decimal('-100.00')
        
        with pytest.raises(Exception):
            customer.full_clean()
    
    def test_customer_soft_delete(self, customer):
        customer.soft_delete()
        customer.refresh_from_db()
        assert customer.is_active is False
    
    def test_customer_type_choices(self, customer):
        assert customer.customer_type == 'regular'
        
        customer.customer_type = 'vip'
        customer.save()
        customer.refresh_from_db()
        assert customer.customer_type == 'vip'


@pytest.mark.django_db
class TestSaleModel:
    
    def test_create_sale(self, sale):
        assert sale.pk is not None
        assert sale.price == Decimal('28500.00')
        assert sale.discount_applied == Decimal('5.00')
        assert sale.is_active is True
    
    def test_sale_str(self, sale):
        expected = f"{sale.dealership.name} → {sale.customer.user.username}: {sale.car_model}"
        assert str(sale) == expected
    
    def test_sale_relationships(self, sale):
        assert sale.dealership is not None
        assert sale.customer is not None
        assert sale.car_model is not None
    
    def test_sale_discount_calculation(self, sale):
        expected_discount_amount = sale.original_price - sale.price
        assert expected_discount_amount == Decimal('1500.00')

@pytest.mark.django_db
class TestCustomerService:
    
    def test_get_all_active_customers(self, customer_factory):
        active1 = customer_factory()
        active2 = customer_factory()
        inactive = customer_factory()
        inactive.soft_delete()
        
        result = CustomerService.get_all_active_customers()
        
        assert result.count() == 2
        assert active1 in result
        assert active2 in result
        assert inactive not in result
    
    def test_get_customer_by_id(self, customer):
        result = CustomerService.get_customer_by_id(customer.id)
        
        assert result is not None
        assert result.id == customer.id
    
    def test_get_customer_by_user(self, customer, regular_user):
        result = CustomerService.get_customer_by_user(regular_user)
        
        assert result is not None
        assert result == customer
    
    def test_create_customer(self, regular_user, db):
        customer = CustomerService.create_customer(
            user=regular_user,
            phone='+9876543210',
            country='GB',
            city='London',
            balance=Decimal('20000.00')
        )
        
        assert customer.pk is not None
        assert customer.user == regular_user
        assert customer.phone == '+9876543210'
    
    def test_update_customer(self, customer):
        data = {
            'phone': '+1111111111',
            'city': 'San Francisco'
        }
        
        updated = CustomerService.update_customer(customer, data)
        
        assert updated.phone == '+1111111111'
        assert updated.city == 'San Francisco'
    
    def test_update_balance(self, customer):
        initial_balance = customer.balance
        amount = Decimal('5000.00')
        
        updated = CustomerService.update_balance(customer, amount)
        
        assert updated.balance == initial_balance + amount
    
    def test_verify_email(self, customer):
        customer.email_verified = False
        customer.save()
        
        verified = CustomerService.verify_email(customer)
        
        assert verified.email_verified is True
    
    def test_get_statistics(self, customer, dealership, car_model):
        for i in range(3):
            Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=car_model,
                price=Decimal('30000.00'),
                original_price=Decimal('32000.00'),
                discount_applied=Decimal('6.25')
            )
        
        stats = CustomerService.get_statistics(customer)
        
        assert stats['customer_id'] == customer.id
        assert stats['username'] == customer.user.username
        assert stats['purchases']['count'] >= 3
        assert stats['purchases']['total'] >= 90000
    
    def test_get_vip_customers(self, customer_factory):
        regular = customer_factory(customer_type='regular')
        vip1 = customer_factory(customer_type='vip')
        vip2 = customer_factory(customer_type='premium')
        
        vip_customers = CustomerService.get_vip_customers()
        
        assert vip1 in vip_customers
        assert vip2 in vip_customers
        assert regular not in vip_customers
    
    def test_register_user(self, db):
        customer = CustomerService.register_user(
            username='newuser',
            email='newuser@test.com',
            password='newpass123',
            first_name='New',
            last_name='User',
            phone='+1234567890',
            country='US',
            city='Boston'
        )
        
        assert customer.pk is not None
        assert customer.user.username == 'newuser'
        assert customer.user.first_name == 'New'
        assert customer.phone == '+1234567890'


@pytest.mark.django_db
class TestSaleService:
    
    def test_get_all_active_sales(self, sale):
        result = SaleService.get_all_active_sales()
        
        assert sale in result
        assert result.count() >= 1
    
    def test_get_sales_by_customer(self, customer, sale):
        result = SaleService.get_sales_by_customer(customer)
        
        assert sale in result
        assert all(s.customer == customer for s in result)
    
    def test_get_sales_by_dealership(self, dealership, sale):
        result = SaleService.get_sales_by_dealership(dealership.id)
        
        assert sale in result
        assert all(s.dealership == dealership for s in result)
    
    def test_create_sale(self, dealership, customer, car_model, dealership_inventory):
        initial_customer_balance = customer.balance
        initial_customer_purchases = customer.total_purchases
        initial_dealership_balance = dealership.balance
        initial_inventory = dealership_inventory.quantity
        
        data = {
            'dealership': dealership,
            'customer': customer,
            'car_model': car_model,
            'price': Decimal('29000.00'),
            'original_price': Decimal('30000.00'),
            'discount_applied': Decimal('3.33')
        }
        
        sale = SaleService.create_sale(data)
        
        assert sale.pk is not None
        
        customer.refresh_from_db()
        assert customer.total_purchases == initial_customer_purchases + 1
        assert customer.balance == initial_customer_balance - Decimal('29000.00')
        assert customer.total_spent >= Decimal('29000.00')
        
        dealership.refresh_from_db()
        assert dealership.total_sales >= 1
        assert dealership.balance >= initial_dealership_balance + Decimal('29000.00')
        
        dealership_inventory.refresh_from_db()
        assert dealership_inventory.quantity == initial_inventory - 1
    
    def test_get_sales_statistics(self, sale):
        stats = SaleService.get_sales_statistics()
        
        assert 'overall' in stats
        assert 'top_dealerships' in stats
        assert 'top_models' in stats
        assert 'promotions_impact' in stats
        
        assert stats['overall']['total_sales'] >= 1
        assert stats['overall']['total_revenue'] >= 0


@pytest.mark.django_db
class TestCustomerAPI:
    
    def test_list_customers_as_admin(self, admin_client, customer_factory):
        customer_factory()
        customer_factory()
        
        url = reverse('customer-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2
    
    def test_list_customers_as_regular_user(self, authenticated_client, customer):
        url = reverse('customer-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
    
    def test_retrieve_customer(self, authenticated_client, customer):
        url = reverse('customer-detail', kwargs={'pk': customer.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_details']['username'] == customer.user.username
    
    def test_register_customer(self, api_client):
        url = reverse('customer-register')
        data = {
            'username': 'newcustomer',
            'email': 'newcustomer@test.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'Customer',
            'phone': '+1234567890',
            'country': 'US',
            'city': 'New York'
        }
        
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Customer.objects.filter(user__username='newcustomer').exists()
    
    def test_me_endpoint(self, authenticated_client, customer):
        url = reverse('customer-me')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['user_details']['username'] == customer.user.username
    
    def test_update_profile(self, authenticated_client, customer):
        url = reverse('customer-update-profile')
        data = {
            'phone': '+9999999999',
            'city': 'Los Angeles'
        }
        
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['phone'] == '+9999999999'
    
    def test_my_purchases(self, authenticated_client, customer, sale):
        url = reverse('customer-my-purchases')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_customer_statistics(self, admin_client, customer):
        url = reverse('customer-statistics', kwargs={'pk': customer.pk})
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'customer_id' in response.data
        assert 'purchases' in response.data
    
    def test_update_balance_as_admin(self, admin_client, customer):
        url = reverse('customer-update-balance', kwargs={'pk': customer.pk})
        data = {'amount': '10000.00'}
        
        initial_balance = customer.balance
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        
        customer.refresh_from_db()
        assert customer.balance == initial_balance + Decimal('10000.00')
    
    def test_update_balance_as_regular_user(self, authenticated_client, customer):
        url = reverse('customer-update-balance', kwargs={'pk': customer.pk})
        data = {'amount': '10000.00'}
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_verify_email_as_admin(self, admin_client, customer):
        customer.email_verified = False
        customer.save()
        
        url = reverse('customer-verify-email', kwargs={'pk': customer.pk})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        
        customer.refresh_from_db()
        assert customer.email_verified is True
    
    def test_vip_customers_endpoint(self, admin_client, customer_factory):
        customer_factory(customer_type='regular')
        customer_factory(customer_type='vip')
        customer_factory(customer_type='premium')
        
        url = reverse('customer-vip-customers')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

@pytest.mark.django_db
class TestSaleAPI:
    
    def test_list_sales_as_admin(self, admin_client, sale):
        url = reverse('sale-list')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_list_sales_as_customer(self, authenticated_client, customer, sale):
        url = reverse('sale-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['customer'] == customer.id
    
    def test_retrieve_sale(self, authenticated_client, sale):
        url = reverse('sale-detail', kwargs={'pk': sale.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['price'] == str(sale.price)
    
    def test_create_sale_as_admin(self, admin_client, dealership, customer, car_model):
        url = reverse('sale-list')
        data = {
            'dealership': dealership.id,
            'customer': customer.id,
            'car_model': car_model.id,
            'price': '27000.00',
            'original_price': '30000.00',
            'discount_applied': '10.00'
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_create_sale_as_regular_user(self, authenticated_client, dealership, customer, car_model):
        url = reverse('sale-list')
        data = {
            'dealership': dealership.id,
            'customer': customer.id,
            'car_model': car_model.id,
            'price': '27000.00',
            'original_price': '30000.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_sales_statistics_endpoint(self, authenticated_client, sale):
        url = reverse('sale-statistics')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'overall' in response.data
        assert 'top_dealerships' in response.data
    
    def test_search_sales(self, authenticated_client, sale):
        url = reverse('sale-list')
        response = authenticated_client.get(url, {'search': sale.customer.user.username})
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_filter_sales_by_dealership(self, authenticated_client, sale):
        url = reverse('sale-list')
        response = authenticated_client.get(url, {'dealership': sale.dealership.id})
        
        assert response.status_code == status.HTTP_200_OK
