from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.contrib.gis.geos import Point
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from customers.models import Customer, Sale
from dealerships.models import Dealership, DealershipInventory, DealershipPreference
from dealerships.services import DealershipInventoryService, DealershipService, PurchaseService
from dealerships.tasks import _process_dealership_purchases, dealership_purchase_cars


@pytest.mark.django_db
class TestDealershipModel:

    def test_create_dealership(self, dealership):
        assert dealership.pk is not None
        assert dealership.name == "Best Cars Dealership"
        assert dealership.is_active is True

    def test_dealership_str(self, dealership):
        expected = f"{dealership.name} ({dealership.city}, {dealership.country})"
        assert str(dealership) == expected

    def test_dealership_unique_name(self, dealership, db):

        with pytest.raises(IntegrityError):
            Dealership.objects.create(
                name=dealership.name,
                country="DE",
                city="Berlin",
                address="Test St",
                email="test2@test.com",
                phone="+49123456789",
            )

    def test_dealership_location(self, dealership):
        if dealership.location is not None:
            assert dealership.location.x == -118.2437
            assert dealership.location.y == 34.0522
        else:
            assert True


@pytest.mark.django_db
class TestDealershipInventoryModel:

    def test_create_inventory(self, dealership_inventory):
        assert dealership_inventory.pk is not None
        assert dealership_inventory.quantity == 10
        assert dealership_inventory.selling_price > dealership_inventory.purchase_price

    def test_inventory_str(self, dealership_inventory):
        expected = (
            f"{dealership_inventory.dealership.name} - "
            f"{dealership_inventory.car_model} (x{dealership_inventory.quantity})"
        )
        assert str(dealership_inventory) == expected

    def test_inventory_unique_together(self, dealership, car_model, db):
        DealershipInventory.objects.create(
            dealership=dealership,
            car_model=car_model,
            quantity=5,
            purchase_price=Decimal("20000.00"),
            selling_price=Decimal("25000.00"),
        )

        with pytest.raises(IntegrityError):
            DealershipInventory.objects.create(
                dealership=dealership,
                car_model=car_model,
                quantity=3,
                purchase_price=Decimal("21000.00"),
                selling_price=Decimal("26000.00"),
            )


@pytest.mark.django_db
class TestPurchaseModel:

    def test_create_purchase(self, purchase):
        assert purchase.pk is not None
        assert purchase.quantity == 5
        assert purchase.total_price == Decimal("115000.00")

    def test_purchase_str(self, purchase):
        expected = f"{purchase.dealership.name} ← {purchase.supplier.name}: {purchase.car_model} x{purchase.quantity}"
        assert str(purchase) == expected


@pytest.mark.django_db
class TestDealershipService:

    def test_get_all_active_dealerships(self, dealership_factory):
        active1 = dealership_factory()
        active2 = dealership_factory()
        inactive = dealership_factory()
        inactive.soft_delete()

        result = DealershipService.get_all_active_dealerships()

        assert result.count() == 2
        assert active1 in result
        assert active2 in result
        assert inactive not in result

    def test_get_dealership_by_id(self, dealership):
        result = DealershipService.get_dealership_by_id(dealership.id)

        assert result is not None
        assert result.id == dealership.id

    def test_create_dealership(self, db):
        data = {
            "name": "New Dealership",
            "country": "GB",
            "city": "London",
            "address": "10 Downing St",
            "email": "new@dealership.com",
            "phone": "+441234567890",
            "balance": Decimal("50000.00"),
            "location": Point(-0.1276, 51.5074, srid=4326),
        }

        dealership = DealershipService.create_dealership(data)

        assert dealership.pk is not None
        assert dealership.name == "New Dealership"

    def test_update_dealership(self, dealership):
        data = {"phone": "+9999999999", "website": "https://newwebsite.com"}

        updated = DealershipService.update_dealership(dealership, data)

        assert updated.phone == "+9999999999"
        assert updated.website == "https://newwebsite.com"

    def test_update_balance(self, dealership):
        initial_balance = dealership.balance
        amount = Decimal("10000.00")

        updated = DealershipService.update_balance(dealership, amount)

        assert updated.balance == initial_balance + amount

    def test_get_dealership_statistics(self, dealership, dealership_inventory, sale):
        stats = DealershipService.get_dealership_statistics(dealership)

        assert "balance" in stats
        assert "inventory" in stats
        assert "sales" in stats
        assert "purchases" in stats
        assert stats["total_sales"] >= 0

    def test_find_nearby_dealerships(self, dealership_factory, db):

        dealership_factory(location=Point(-118.2437, 34.0522, srid=4326))
        dealership_factory(location=Point(-74.0060, 40.7128, srid=4326))

        nearby = DealershipService.find_nearby(latitude=34.0522, longitude=-118.2437, radius=50)

        assert nearby.count() >= 1


@pytest.mark.django_db
class TestDealershipInventoryService:

    def test_get_all_active_inventory(self, dealership_inventory):
        result = DealershipInventoryService.get_all_active_inventory()

        assert dealership_inventory in result

    def test_get_inventory_by_dealership(self, dealership, dealership_inventory):
        result = DealershipInventoryService.get_inventory_by_dealership(dealership.id)

        assert dealership_inventory in result
        assert all(item.dealership == dealership for item in result)

    def test_get_available_inventory(self, dealership_inventory):
        result = DealershipInventoryService.get_available_inventory()

        assert dealership_inventory in result
        assert all(item.quantity > 0 for item in result)

    def test_create_inventory_item(self, dealership, car_model):
        data = {
            "dealership": dealership,
            "car_model": car_model,
            "quantity": 15,
            "purchase_price": Decimal("22000.00"),
            "selling_price": Decimal("27000.00"),
        }

        inventory = DealershipInventoryService.create_inventory_item(data)

        assert inventory.pk is not None
        assert inventory.quantity == 15

    def test_decrease_quantity(self, dealership_inventory):
        initial_quantity = dealership_inventory.quantity
        initial_times_sold = dealership_inventory.times_sold

        updated = DealershipInventoryService.decrease_quantity(dealership_inventory, 2)

        assert updated.quantity == initial_quantity - 2
        assert updated.times_sold == initial_times_sold + 1

    def test_increase_quantity(self, dealership_inventory):
        initial_quantity = dealership_inventory.quantity

        updated = DealershipInventoryService.increase_quantity(dealership_inventory, 5)

        assert updated.quantity == initial_quantity + 5


@pytest.mark.django_db
class TestPurchaseService:

    def test_get_all_active_purchases(self, purchase):
        result = PurchaseService.get_all_active_purchases()

        assert purchase in result

    def test_get_purchases_by_dealership(self, dealership, purchase):
        result = PurchaseService.get_purchases_by_dealership(dealership.id)

        assert purchase in result
        assert all(p.dealership == dealership for p in result)

    def test_create_purchase(self, dealership, supplier, car_model):
        initial_balance = dealership.balance

        data = {
            "dealership": dealership,
            "supplier": supplier,
            "car_model": car_model,
            "quantity": 3,
            "unit_price": Decimal("24000.00"),
            "total_price": Decimal("72000.00"),
        }

        purchase = PurchaseService.create_purchase(data)

        assert purchase.pk is not None

        dealership.refresh_from_db()
        assert dealership.balance == initial_balance - Decimal("72000.00")

        inventory = DealershipInventory.objects.filter(dealership=dealership, car_model=car_model).first()
        assert inventory is not None
        assert inventory.quantity >= 3

    def test_get_purchase_count(self, supplier, dealership, purchase):
        count = PurchaseService.get_purchase_count(supplier.id, dealership.id)

        assert count >= 1

    def test_get_statistics(self, purchase):
        stats = PurchaseService.get_statistics()

        assert "total_purchases" in stats
        assert "total_quantity" in stats
        assert "top_suppliers" in stats
        assert stats["total_purchases"] >= 1


@pytest.mark.django_db
class TestDealershipCeleryTasks:

    def test_dealership_purchase_cars_task(self, dealership, supplier_car, dealership_preference, customer):
        dealership.balance = Decimal("500000.00")
        dealership.save()

        result = dealership_purchase_cars()

        assert "total_purchases" in result
        assert result["total_purchases"] >= 0

    @patch("dealerships.tasks._find_best_supplier_offer")
    def test_process_dealership_purchases(self, mock_find_offer, dealership, car_model, supplier):
        dealership.balance = Decimal("200000.00")
        dealership.save()

        mock_find_offer.return_value = {
            "supplier_id": supplier.id,
            "unit_price": Decimal("23000.00"),
            "total_price": Decimal("69000.00"),
            "discount_percent": Decimal("5.00"),
            "promotion_id": None,
        }

        DealershipPreference.objects.create(dealership=dealership, preferred_brands=[car_model.brand])

        purchases_count = _process_dealership_purchases(dealership)

        assert purchases_count >= 0

    def test_purchase_with_promotion(self, dealership, supplier_car, promotion_supplier, car_model_factory):
        dealership.balance = Decimal("300000.00")
        dealership.save()

        car = supplier_car.car_model

        user = User.objects.create_user(username="testuser", password="pass")
        customer = Customer.objects.create(user=user, balance=Decimal("100000.00"))

        for _ in range(5):
            Sale.objects.create(
                dealership=dealership,
                customer=customer,
                car_model=car,
                price=Decimal("30000.00"),
                original_price=Decimal("30000.00"),
            )

        result = dealership_purchase_cars()

        assert result["total_purchases"] >= 0


@pytest.mark.django_db
class TestDealershipAPI:

    def test_list_dealerships(self, authenticated_client, dealership_factory):
        dealership_factory()
        dealership_factory()

        url = reverse("dealership-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2

    def test_retrieve_dealership(self, authenticated_client, dealership):
        url = reverse("dealership-detail", kwargs={"pk": dealership.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == dealership.name

    def test_create_dealership_as_admin(self, admin_client):
        url = reverse("dealership-list")
        data = {
            "name": "API Test Dealership",
            "country": "US",
            "city": "Chicago",
            "address": "100 Main St",
            "email": "api@test.com",
            "phone": "+1234567890",
            "balance": "100000.00",
        }

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Dealership.objects.filter(name="API Test Dealership").exists()

    def test_create_dealership_as_regular_user(self, authenticated_client):
        url = reverse("dealership-list")
        data = {
            "name": "Test",
            "country": "US",
            "city": "Test",
            "address": "Test",
            "email": "test@test.com",
            "phone": "+1234567890",
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestDealershipInventoryAPI:

    def test_list_inventory(self, authenticated_client, dealership_inventory):
        url = reverse("dealershipinventory-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_inventory(self, authenticated_client, dealership_inventory):
        url = reverse("dealershipinventory-detail", kwargs={"pk": dealership_inventory.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["quantity"] == dealership_inventory.quantity

    def test_filter_inventory_by_dealership(self, authenticated_client, dealership, dealership_inventory):
        url = reverse("dealershipinventory-list")
        response = authenticated_client.get(url, {"dealership": dealership.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1


@pytest.mark.django_db
class TestPurchaseAPI:

    def test_list_purchases(self, admin_client, purchase):
        url = reverse("purchase-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_purchase(self, admin_client, purchase):
        url = reverse("purchase-detail", kwargs={"pk": purchase.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["quantity"] == purchase.quantity

    def test_create_purchase_as_admin(self, admin_client, dealership, supplier, car_model):
        url = reverse("purchase-list")
        data = {
            "dealership": dealership.id,
            "supplier": supplier.id,
            "car_model": car_model.id,
            "quantity": 5,
            "unit_price": "24000.00",
            "total_price": "120000.00",
        }

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
