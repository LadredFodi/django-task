import pytest
from decimal import Decimal
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from cars.models import CarModel
from customers.models import Sale
from cars.services import CarModelService


@pytest.mark.django_db
class TestCarModel:
    
    def test_create_car_model(self, car_model):
        
        assert car_model.pk is not None
        assert car_model.brand == 'Toyota'
        assert car_model.model == 'Camry'
        assert car_model.year == 2023
        assert car_model.is_active is True
    
    def test_car_model_str(self, car_model):

        expected = "Toyota Camry 2023 (Gasoline)"
        assert str(car_model) == expected
    
    def test_car_model_unique_together(self, db):
        
        CarModel.objects.create(
            brand='BMW',
            model='X5',
            year=2023,
            body_type='suv',
            color='black',
            fuel_type='gasoline',
            engine_volume=Decimal('3.0'),
            transmission='automatic',
            drive_type='awd'
        )
        
        with pytest.raises(IntegrityError):
            CarModel.objects.create(
                brand='BMW',
                model='X5',
                year=2023,
                body_type='suv',
                color='black',
                fuel_type='gasoline',
                engine_volume=Decimal('3.0'),
                transmission='automatic',
                drive_type='awd'
            )
    
    def test_car_model_soft_delete(self, car_model):
        assert car_model.is_active is True
        car_model.soft_delete()
        car_model.refresh_from_db()
        assert car_model.is_active is False
    
    def test_car_model_restore(self, car_model):
        car_model.soft_delete()
        assert car_model.is_active is False
        car_model.restore()
        car_model.refresh_from_db()
        assert car_model.is_active is True
    
    def test_car_model_validators(self, db):
        with pytest.raises(Exception):
            car = CarModel(
                brand='Test',
                model='Test',
                year=3000,
                body_type='sedan',
                fuel_type='gasoline',
                engine_volume=Decimal('2.0'),
                transmission='automatic',
                drive_type='fwd'
            )
            car.full_clean()


@pytest.mark.django_db
class TestCarModelService:
    
    def test_get_all_active_cars(self, car_model_factory):
        active1 = car_model_factory()
        active2 = car_model_factory()
        inactive = car_model_factory()
        inactive.soft_delete()
        
        result = CarModelService.get_all_active_cars()
        
        assert result.count() == 2
        assert active1 in result
        assert active2 in result
        assert inactive not in result
    
    def test_get_car_by_id(self, car_model):
        result = CarModelService.get_car_by_id(car_model.id)
        assert result is not None
        assert result.id == car_model.id
    
    def test_get_car_by_id_inactive(self, car_model):
        car_model.soft_delete()
        result = CarModelService.get_car_by_id(car_model.id)
        assert result is None
    
    def test_get_car_by_id_not_exists(self):
        result = CarModelService.get_car_by_id(99999)
        assert result is None
    
    def test_create_car_model(self, db):
        data = {
            'brand': 'Honda',
            'model': 'Civic',
            'year': 2023,
            'body_type': 'sedan',
            'color': 'white',
            'fuel_type': 'gasoline',
            'engine_volume': Decimal('1.5'),
            'transmission': 'cvt',
            'drive_type': 'fwd'
        }
        
        car = CarModelService.create_car_model(data)
        
        assert car.pk is not None
        assert car.brand == 'Honda'
        assert car.model == 'Civic'
    
    def test_update_car_model(self, car_model):
        data = {
            'color': 'red',
            'horsepower': 250
        }
        
        updated = CarModelService.update_car_model(car_model, data)
        
        assert updated.color == 'red'
        assert updated.horsepower == 250
        assert updated.brand == car_model.brand
    
    def test_soft_delete_car_model(self, car_model):
        assert car_model.is_active is True
        CarModelService.soft_delete_car_model(car_model)
        car_model.refresh_from_db()
        assert car_model.is_active is False
    
    def test_restore_car_model(self, car_model):
        car_model.soft_delete()
        restored = CarModelService.restore_car_model(car_model)
        assert restored.is_active is True
    
    def test_get_popular_models(self, car_model_factory, dealership, customer):
        
        car1 = car_model_factory()
        car2 = car_model_factory()
        car3 = car_model_factory()
        
        for _ in range(5):
            Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=car1,
                price=Decimal('30000'),
                original_price=Decimal('30000')
            )
        
        for _ in range(3):
            Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=car2,
                price=Decimal('25000'),
                original_price=Decimal('25000')
            )
        
        popular = CarModelService.get_popular_models(limit=2)
        
        assert len(popular) == 2
        assert popular[0] == car1
        assert popular[1] == car2
    
    def test_get_all_brands(self, car_model_factory):
        car_model_factory(brand='Toyota')
        car_model_factory(brand='Honda')
        car_model_factory(brand='Toyota')
        
        brands = CarModelService.get_all_brands()
        
        assert len(brands) == 2
        assert 'Toyota' in brands
        assert 'Honda' in brands
    
    def test_filter_by_criteria(self, car_model_factory):
        toyota = car_model_factory(brand='Toyota', year=2023, body_type='sedan')
        honda = car_model_factory(brand='Honda', year=2022, body_type='suv')
        bmw = car_model_factory(brand='BMW', year=2024, body_type='sedan')
        
        result = CarModelService.filter_by_criteria(brand='Toyota')
        assert toyota in result
        assert honda not in result
        
        result = CarModelService.filter_by_criteria(year_min=2023)
        assert toyota in result
        assert bmw in result
        assert honda not in result
        
        result = CarModelService.filter_by_criteria(body_type='sedan')
        assert toyota in result
        assert bmw in result
        assert honda not in result
        
        result = CarModelService.filter_by_criteria(
            brand='Toyota',
            year_min=2023,
            body_type='sedan'
        )
        assert result.count() == 1
        assert toyota in result

@pytest.mark.django_db
class TestCarModelAPI:
    
    def test_list_cars_authenticated(self, authenticated_client, car_model_factory):
        car_model_factory()
        car_model_factory()
        
        url = reverse('carmodel-list')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2
    
    def test_list_cars_unauthenticated(self, api_client, car_model):
        url = reverse('carmodel-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_retrieve_car(self, authenticated_client, car_model):
        url = reverse('carmodel-detail', kwargs={'pk': car_model.pk})
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['brand'] == car_model.brand
        assert response.data['model'] == car_model.model
    
    def test_create_car_as_admin(self, admin_client):
        url = reverse('carmodel-list')
        data = {
            'brand': 'Mazda',
            'model': 'CX-5',
            'year': 2023,
            'body_type': 'suv',
            'color': 'blue',
            'fuel_type': 'gasoline',
            'engine_volume': '2.5',
            'transmission': 'automatic',
            'drive_type': 'awd'
        }
        
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['brand'] == 'Mazda'
        assert CarModel.objects.filter(brand='Mazda', model='CX-5').exists()
    
    def test_create_car_as_regular_user(self, authenticated_client):
        url = reverse('carmodel-list')
        data = {
            'brand': 'Mazda',
            'model': 'CX-5',
            'year': 2023,
            'body_type': 'suv',
            'fuel_type': 'gasoline',
            'engine_volume': '2.5',
            'transmission': 'automatic',
            'drive_type': 'awd'
        }
        
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_update_car_as_admin(self, admin_client, car_model):
        url = reverse('carmodel-detail', kwargs={'pk': car_model.pk})
        data = {
            'color': 'silver',
            'horsepower': 220
        }
        
        response = admin_client.patch(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['color'] == 'silver'
        assert response.data['horsepower'] == 220
    
    def test_delete_car_as_admin(self, admin_client, car_model):
        url = reverse('carmodel-detail', kwargs={'pk': car_model.pk})
        response = admin_client.delete(url)
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        car_model.refresh_from_db()
        assert car_model.is_active is False
    
    def test_popular_cars_endpoint(self, authenticated_client, car_model_factory, dealership, customer):
        
        
        car1 = car_model_factory()
        
        for _ in range(3):
            Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=car1,
                price=Decimal('30000'),
                original_price=Decimal('30000')
            )
        
        url = reverse('carmodel-popular')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
    
    def test_brands_endpoint(self, authenticated_client, car_model_factory):
        car_model_factory(brand='Toyota')
        car_model_factory(brand='Honda')
        
        url = reverse('carmodel-brands')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Toyota' in response.data
        assert 'Honda' in response.data
    
    def test_restore_car_endpoint(self, admin_client, car_model):
        car_model.soft_delete()
        
        url = reverse('carmodel-restore', kwargs={'pk': car_model.pk})
        response = admin_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        car_model.refresh_from_db()
        assert car_model.is_active is True
    
    def test_search_cars(self, authenticated_client, car_model_factory):
        car_model_factory(brand='Toyota', model='Camry')
        car_model_factory(brand='Honda', model='Accord')
        
        url = reverse('carmodel-list')
        response = authenticated_client.get(url, {'search': 'Toyota'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['brand'] == 'Toyota'
    
    def test_filter_cars(self, authenticated_client, car_model_factory):
        car_model_factory(brand='Toyota', body_type='sedan', fuel_type='gasoline')
        car_model_factory(brand='Honda', body_type='suv', fuel_type='hybrid')
        
        url = reverse('carmodel-list')
        response = authenticated_client.get(url, {'body_type': 'sedan'})
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['body_type'] == 'sedan'
    
    def test_ordering_cars(self, authenticated_client, car_model_factory):
        car_model_factory(brand='Toyota', year=2021)
        car_model_factory(brand='Honda', year=2023)
        car_model_factory(brand='BMW', year=2022)
        
        url = reverse('carmodel-list')
        response = authenticated_client.get(url, {'ordering': 'year'})
        
        assert response.status_code == status.HTTP_200_OK
        years = [item['year'] for item in response.data['results']]
        assert years == sorted(years)
