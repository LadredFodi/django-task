import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status

from offers.models import Offer
from offers.services import OfferService
from offers.tasks import process_customer_offer, _find_matching_dealerships, _execute_purchase


@pytest.mark.django_db
class TestOfferModel:
    
    def test_create_offer(self, offer):
        assert offer.pk is not None
        assert offer.status == 'pending'
        assert offer.max_price == Decimal('35000.00')
        assert offer.is_active is True
    
    def test_offer_str(self, offer):
        expected = f"Offer #{offer.id}: {offer.customer.user.username} → {offer.car_model} (max ${offer.max_price})"
        assert str(offer) == expected
    
    def test_offer_status_choices(self, offer):
        valid_statuses = ['pending', 'processing', 'completed', 'cancelled', 'expired']
        
        for status in valid_statuses:
            offer.status = status
            offer.save()
            offer.refresh_from_db()
            assert offer.status == status
    
    def test_offer_relationships(self, offer):
        assert offer.customer is not None
        assert offer.car_model is not None
        assert offer.matched_dealership is None
    
    def test_offer_search_results_default(self, offer):
        assert isinstance(offer.search_results, dict)



@pytest.mark.django_db
class TestOfferService:
    
    def test_get_all_active_offers(self, offer):
        result = OfferService.get_all_active_offers()
        
        assert offer in result
        assert result.count() >= 1
    
    def test_get_offer_by_id(self, offer):
        result = OfferService.get_offer_by_id(offer.id)
        
        assert result is not None
        assert result.id == offer.id
    
    def test_get_offer_by_id_inactive(self, offer):
        offer.soft_delete()
        result = OfferService.get_offer_by_id(offer.id)
        
        assert result is None
    
    def test_get_offers_by_customer(self, customer, offer):
        result = OfferService.get_offers_by_customer(customer)
        
        assert offer in result
        assert all(o.customer == customer for o in result)
    
    def test_get_pending_offers(self, offer):
        result = OfferService.get_pending_offers()
        
        assert offer in result
        assert all(o.status == 'pending' for o in result)
    
    def test_create_offer(self, customer, car_model, dealership_inventory):
        offer = OfferService.create_offer(
            customer=customer,
            car_model_id=car_model.id,
            max_price=32000.00
        )
        
        assert offer.pk is not None
        assert offer.customer == customer
        assert offer.car_model == car_model
        assert offer.max_price == Decimal('32000.00')
    
    def test_search_matching_dealerships(self, offer, dealership_inventory):
        dealership_inventory.selling_price = Decimal('30000.00')
        dealership_inventory.save()
        
        results = OfferService.search_matching_dealerships(offer)
        
        assert len(results) >= 1
        assert results[0]['price'] <= float(offer.max_price)
        
        offer.refresh_from_db()
        assert offer.matched_dealership is not None
        assert offer.matched_price is not None
    
    def test_search_matching_dealerships_no_match(self, offer, dealership_inventory):
        dealership_inventory.selling_price = Decimal('50000.00')
        dealership_inventory.save()
        
        results = OfferService.search_matching_dealerships(offer)
        
        assert len(results) == 0
    
    def test_process_offer(self, offer, dealership_inventory):
        assert offer.status == 'pending'
        
        processed = OfferService.process_offer(offer)
        
        assert processed.status == 'processing'
        assert processed.processed_at is not None
    
    def test_complete_offer(self, offer):
        completed = OfferService.complete_offer(offer)
        
        assert completed.status == 'completed'
        assert completed.completed_at is not None
    
    def test_cancel_offer(self, offer):
        cancelled = OfferService.cancel_offer(offer)
        
        assert cancelled.status == 'cancelled'
    
    def test_expire_old_offers(self, customer, car_model):
        expired_offer = Offer.objects.create(
            customer=customer,
            car_model=car_model,
            max_price=Decimal('30000.00'),
            status='pending',
            expires_at=timezone.now() - timedelta(days=1)
        )
        
        count = OfferService.expire_old_offers()
        
        assert count >= 1
        
        expired_offer.refresh_from_db()
        assert expired_offer.status == 'expired'
    
    def test_get_statistics(self, offer):
        stats = OfferService.get_statistics()
        
        assert 'total' in stats
        assert 'by_status' in stats
        assert 'top_models' in stats
        assert stats['total']['total_offers'] >= 1



@pytest.mark.django_db
class TestOfferCeleryTasks:
    
    def test_process_customer_offer_success(
        self, offer, dealership_inventory, customer
    ):
        dealership_inventory.selling_price = Decimal('30000.00')
        dealership_inventory.quantity = 5
        dealership_inventory.save()
        
        customer.balance = Decimal('50000.00')
        customer.save()
        
        result = process_customer_offer(offer.id)
        
        assert result['success'] is True
        assert 'sale_id' in result
        
        offer.refresh_from_db()
        assert offer.status == 'completed'
    
    def test_process_customer_offer_not_found(self):
        result = process_customer_offer(99999)
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_process_customer_offer_wrong_status(self, offer):      
        offer.status = 'completed'
        offer.save()
        
        result = process_customer_offer(offer.id)
        
        assert result['success'] is False
        assert 'status' in result['error']
    
    def test_process_customer_offer_no_matching_dealerships(
        self, offer, dealership_inventory
    ):
        dealership_inventory.selling_price = Decimal('100000.00')
        dealership_inventory.save()
        
        result = process_customer_offer(offer.id)
        
        assert result['success'] is False
        
        offer.refresh_from_db()
        assert offer.status == 'cancelled'
    
    def test_process_customer_offer_insufficient_balance(
        self, offer, dealership_inventory, customer
    ):
        dealership_inventory.selling_price = Decimal('30000.00')
        dealership_inventory.save()
        
        customer.balance = Decimal('1000.00')
        customer.save()
        
        result = process_customer_offer(offer.id)
        
        assert result['success'] is False
        assert 'balance' in result['error'].lower()
    
    def test_find_matching_dealerships(self, offer, dealership_inventory):
        dealership_inventory.selling_price = Decimal('28000.00')
        dealership_inventory.quantity = 3
        dealership_inventory.save()
        
        matches = _find_matching_dealerships(offer)
        
        assert len(matches) >= 1
        assert matches[0]['final_price'] <= float(offer.max_price)
        assert matches[0]['dealership_id'] == dealership_inventory.dealership.id
    
    def test_find_matching_dealerships_with_promotion(
        self, offer, dealership_inventory, promotion_dealership
    ):
        dealership_inventory.selling_price = Decimal('32000.00')
        dealership_inventory.quantity = 3
        dealership_inventory.save()
        
        matches = _find_matching_dealerships(offer)
        
        if len(matches) > 0:
            assert matches[0]['final_price'] < matches[0]['base_price']
            assert matches[0]['discount_percent'] > 0
    
    def test_execute_purchase(self, offer, dealership_inventory, customer):
        dealership_inventory.selling_price = Decimal('30000.00')
        dealership_inventory.quantity = 5
        dealership_inventory.save()
        
        customer.balance = Decimal('50000.00')
        customer.save()
        
        dealership_match = {
            'dealership_id': dealership_inventory.dealership.id,
            'inventory_id': dealership_inventory.id,
            'base_price': float(dealership_inventory.selling_price),
            'discount_percent': 5.0,
            'final_price': float(dealership_inventory.selling_price * Decimal('0.95')),
            'promotion_id': None
        }
        
        sale = _execute_purchase(offer, dealership_match)
        
        assert sale is not None
        assert sale.customer == customer
        assert sale.car_model == offer.car_model
        
        customer.refresh_from_db()
        assert customer.balance < Decimal('50000.00')
        assert customer.total_purchases >= 1
        
        dealership_inventory.refresh_from_db()
        assert dealership_inventory.quantity == 4
    
    def test_execute_purchase_insufficient_inventory(
        self, offer, dealership_inventory, customer
    ):
        dealership_inventory.quantity = 0
        dealership_inventory.save()
        
        customer.balance = Decimal('50000.00')
        customer.save()
        
        dealership_match = {
            'dealership_id': dealership_inventory.dealership.id,
            'inventory_id': dealership_inventory.id,
            'base_price': 30000.0,
            'discount_percent': 0,
            'final_price': 30000.0,
            'promotion_id': None
        }
        
        sale = _execute_purchase(offer, dealership_match)
        
        assert sale is None



@pytest.mark.django_db
class TestOfferAPI:

    def test_list_offers(self, authenticated_client, offer):
        url = reverse('offer-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_list_offers_as_customer(self, authenticated_client, customer, offer):
        url = reverse('offer-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['customer'] == customer.id
    
    def test_retrieve_offer(self, authenticated_client, offer):
        url = reverse('offer-detail', kwargs={'pk': offer.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['max_price'] == str(offer.max_price)
        assert response.data['status'] == offer.status
    
    def test_create_offer(self, authenticated_client, customer, car_model):
        url = reverse('offer-list')
        data = {
            'car_model': car_model.id,
            'max_price': '33000.00'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert Offer.objects.filter(
            customer=customer,
            car_model=car_model
        ).exists()
    
    def test_update_offer(self, authenticated_client, offer):
        url = reverse('offer-detail', kwargs={'pk': offer.pk})
        data = {
            'max_price': '37000.00',
            'notes': 'Updated notes'
        }
        
        response = authenticated_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['max_price'] == '37000.00'
    
    def test_delete_offer(self, authenticated_client, offer):
        url = reverse('offer-detail', kwargs={'pk': offer.pk})
        response = authenticated_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        offer.refresh_from_db()
        assert offer.is_active is False
    
    def test_filter_offers_by_status(self, authenticated_client, customer, car_model):
        Offer.objects.create(
            customer=customer,
            car_model=car_model,
            max_price=Decimal('30000.00'),
            status='pending'
        )
        Offer.objects.create(
            customer=customer,
            car_model=car_model,
            max_price=Decimal('35000.00'),
            status='completed'
        )
        
        url = reverse('offer-list')
        response = authenticated_client.get(url, {'status': 'pending'})
        
        assert response.status_code == status.HTTP_200_OK
        assert all(item['status'] == 'pending' for item in response.data['results'])
    
    def test_search_offers(self, authenticated_client, offer):
        url = reverse('offer-list')
        response = authenticated_client.get(
            url,
            {'search': offer.customer.user.username}
        )
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_process_offer_endpoint(self, admin_client, offer):
        offer.status = 'pending'
        offer.save()
        
        url = reverse('offer-process', kwargs={'pk': offer.pk})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        offer.refresh_from_db()
        assert offer.status == 'processing'
    
    def test_cancel_offer_endpoint(self, authenticated_client, regular_user, customer, car_model, db):
        assert customer.user == regular_user
        
        offer = Offer.objects.create(
            customer=customer,
            car_model=car_model,
            max_price=Decimal('35000.00'),
            status='pending'
        )
        
        url = reverse('offer-cancel', kwargs={'pk': offer.pk})
        response = authenticated_client.post(url)
        
        if response.status_code == 403:
            print(f"Request user: {authenticated_client.handler._force_user}")
            print(f"Offer customer user: {offer.customer.user}")
            print(f"Response data: {response.data}")
        
        assert response.status_code == status.HTTP_200_OK
        
        offer.refresh_from_db()
        assert offer.status == 'cancelled'
    
    def test_offer_statistics_endpoint(self, admin_client, offer):
        url = reverse('offer-statistics')
        response = admin_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert 'by_status' in response.data
