from decimal import Decimal
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from dealerships.models import Purchase
from suppliers.models import Supplier, SupplierCar
from suppliers.services import SupplierCarService, SupplierDiscountService, SupplierService
from suppliers.tasks import _update_dealership_supplier_preferences, update_supplier_preferences


@pytest.mark.django_db
class TestSupplierModel:

    def test_create_supplier(self, supplier):
        assert supplier.pk is not None
        assert supplier.name == "Global Auto Supplier"
        assert supplier.rating == Decimal("7.5")
        assert supplier.is_active is True

    def test_supplier_str(self, supplier):
        expected = f"{supplier.name} ({supplier.country})"
        assert str(supplier) == expected

    def test_supplier_unique_name(self, supplier, db):
        with pytest.raises(IntegrityError):
            Supplier.objects.create(
                name=supplier.name, country="US", founded_year=2010, email="another@test.com", rating=Decimal("5.0")
            )

    def test_supplier_rating_validators(self, supplier):
        supplier.rating = Decimal("10.0")

        with pytest.raises(Exception):
            supplier.full_clean()


@pytest.mark.django_db
class TestSupplierCarModel:

    def test_create_supplier_car(self, supplier_car):
        assert supplier_car.pk is not None
        assert supplier_car.price == Decimal("23000.00")
        assert supplier_car.available_quantity == 50

    def test_supplier_car_str(self, supplier_car):
        expected = f"{supplier_car.supplier.name} - {supplier_car.car_model} (${supplier_car.price})"
        assert str(supplier_car) == expected

    def test_supplier_car_unique_together(self, supplier, car_model, db):
        SupplierCar.objects.create(
            supplier=supplier, car_model=car_model, price=Decimal("25000.00"), available_quantity=10
        )

        with pytest.raises(IntegrityError):
            SupplierCar.objects.create(
                supplier=supplier, car_model=car_model, price=Decimal("26000.00"), available_quantity=15
            )


@pytest.mark.django_db
class TestSupplierDiscountModel:

    def test_create_supplier_discount(self, supplier_discount):
        assert supplier_discount.pk is not None
        assert supplier_discount.discount_percent == Decimal("5.00")
        assert supplier_discount.is_applied is False

    def test_supplier_discount_str(self, supplier_discount):
        expected = (
            f"{supplier_discount.supplier.name} → "
            f"{supplier_discount.dealership.name}: {supplier_discount.discount_percent}%"
        )
        assert str(supplier_discount) == expected


@pytest.mark.django_db
class TestSupplierService:

    def test_get_all_active_suppliers(self, supplier_factory):
        active1 = supplier_factory()
        active2 = supplier_factory()
        inactive = supplier_factory()
        inactive.soft_delete()

        result = SupplierService.get_all_active_suppliers()

        assert result.count() == 2
        assert active1 in result
        assert active2 in result
        assert inactive not in result

    def test_get_supplier_by_id(self, supplier):
        result = SupplierService.get_supplier_by_id(supplier.id)

        assert result is not None
        assert result.id == supplier.id

    def test_create_supplier(self, db):
        data = {
            "name": "New Supplier",
            "country": "FR",
            "founded_year": 2015,
            "email": "new@supplier.com",
            "rating": Decimal("6.5"),
        }

        supplier = SupplierService.create_supplier(data)

        assert supplier.pk is not None
        assert supplier.name == "New Supplier"

    def test_update_supplier(self, supplier):
        data = {"phone": "+49987654321", "website": "https://newsupplier.com", "rating": Decimal("7.8")}

        updated = SupplierService.update_supplier(supplier, data)

        assert updated.phone == "+49987654321"
        assert updated.rating == Decimal("7.8")

    def test_get_supplier_statistics(self, supplier, supplier_car, purchase):
        stats = SupplierService.get_supplier_statistics(supplier)

        assert "supplier_id" in stats
        assert "supplier_name" in stats
        assert "total_car_models" in stats
        assert "total_available_cars" in stats
        assert "top_partner_dealerships" in stats
        assert stats["supplier_id"] == supplier.id


@pytest.mark.django_db
class TestSupplierCarService:

    def test_get_all_active_supplier_cars(self, supplier_car):
        result = SupplierCarService.get_all_active_supplier_cars()

        assert supplier_car in result

    def test_get_supplier_cars_by_supplier(self, supplier, supplier_car):
        result = SupplierCarService.get_supplier_cars_by_supplier(supplier.id)

        assert supplier_car in result
        assert all(sc.supplier == supplier for sc in result)

    def test_create_supplier_car(self, supplier, car_model):
        data = {
            "supplier": supplier,
            "car_model": car_model,
            "price": Decimal("24500.00"),
            "available_quantity": 30,
            "delivery_days": 12,
        }

        supplier_car = SupplierCarService.create_supplier_car(data)

        assert supplier_car.pk is not None
        assert supplier_car.price == Decimal("24500.00")

    def test_update_supplier_car(self, supplier_car):
        data = {"price": Decimal("22500.00"), "available_quantity": 40}

        updated = SupplierCarService.update_supplier_car(supplier_car, data)

        assert updated.price == Decimal("22500.00")
        assert updated.available_quantity == 40

    def test_get_best_prices(self, supplier_car, car_model, supplier_factory):
        supplier2 = supplier_factory()
        SupplierCar.objects.create(
            supplier=supplier2, car_model=car_model, price=Decimal("21000.00"), available_quantity=20
        )

        best_prices = SupplierCarService.get_best_prices()

        car_offer = best_prices.filter(car_model=car_model).first()
        assert car_offer is not None
        assert car_offer.price == Decimal("21000.00")


@pytest.mark.django_db
class TestSupplierDiscountService:

    def test_get_all_active_supplier_discounts(self, supplier_discount):
        result = SupplierDiscountService.get_all_active_supplier_discounts()

        assert supplier_discount in result

    def test_create_supplier_discount(self, supplier, dealership):
        data = {"supplier": supplier, "dealership": dealership, "discount_percent": Decimal("7.5"), "min_purchases": 15}

        discount = SupplierDiscountService.create_supplier_discount(data)

        assert discount.pk is not None
        assert discount.discount_percent == Decimal("7.5")

    def test_update_discount(self, supplier_discount):
        data = {"discount_percent": Decimal("10.0"), "min_purchases": 20}

        updated = SupplierDiscountService.update_discount(supplier_discount, data)

        assert updated.discount_percent == Decimal("10.0")
        assert updated.min_purchases == 20

    def test_check_and_apply_discount_sufficient_purchases(self, supplier, dealership, supplier_discount, car_model):
        for _ in range(supplier_discount.min_purchases):
            Purchase.objects.create(
                dealership=dealership,
                supplier=supplier,
                car_model=car_model,
                quantity=1,
                unit_price=Decimal("20000.00"),
                total_price=Decimal("20000.00"),
            )

        result = SupplierDiscountService.check_and_apply_discount(supplier.id, dealership.id)

        assert result is not None
        assert result.is_applied is True

    def test_check_and_apply_discount_insufficient_purchases(self, supplier, dealership, supplier_discount):
        result = SupplierDiscountService.check_and_apply_discount(supplier.id, dealership.id)

        assert result is None


@pytest.mark.django_db
class TestSupplierCeleryTasks:

    def test_update_supplier_preferences_task(self, dealership, supplier_car, dealership_inventory):
        result = update_supplier_preferences()

        assert "updates_count" in result
        assert result["updates_count"] >= 0

    def test_update_dealership_supplier_preferences(self, dealership, supplier_car, dealership_inventory):
        dealership_inventory.quantity = 10
        dealership_inventory.purchase_price = Decimal("25000.00")
        dealership_inventory.save()

        supplier2 = Supplier.objects.create(
            name="Better Supplier", country="US", founded_year=2010, email="better@supplier.com", rating=Decimal("7.0")
        )
        SupplierCar.objects.create(
            supplier=supplier2,
            car_model=dealership_inventory.car_model,
            price=Decimal("20000.00"),
            available_quantity=50,
        )

        result = _update_dealership_supplier_preferences(dealership)

        assert isinstance(result, bool)

    @patch("suppliers.tasks._calculate_potential_price")
    def test_update_dealership_with_promotion(self, mock_calculate, dealership, supplier_car, dealership_inventory):
        mock_calculate.return_value = Decimal("19000.00")

        result = _update_dealership_supplier_preferences(dealership)

        assert isinstance(result, bool)


@pytest.mark.django_db
class TestSupplierAPI:

    def test_list_suppliers(self, authenticated_client, supplier_factory):
        supplier_factory()
        supplier_factory()

        url = reverse("supplier-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 2

    def test_retrieve_supplier(self, authenticated_client, supplier):
        url = reverse("supplier-detail", kwargs={"pk": supplier.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == supplier.name

    def test_create_supplier_as_admin(self, admin_client):
        url = reverse("supplier-list")
        data = {
            "name": "API Test Supplier",
            "country": "IT",
            "founded_year": 2018,
            "email": "api@supplier.com",
            "rating": "6.5",
        }

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Supplier.objects.filter(name="API Test Supplier").exists()

    def test_create_supplier_as_regular_user(self, authenticated_client):
        url = reverse("supplier-list")
        data = {"name": "Test Supplier", "country": "US", "founded_year": 2020, "email": "test@supplier.com"}

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_supplier_statistics_endpoint(self, admin_client, supplier):
        url = reverse("supplier-statistics", kwargs={"pk": supplier.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "supplier_id" in response.data
        assert "total_car_models" in response.data


@pytest.mark.django_db
class TestSupplierCarAPI:

    def test_list_supplier_cars(self, authenticated_client, supplier_car):
        url = reverse("suppliercar-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_supplier_car(self, authenticated_client, supplier_car):
        url = reverse("suppliercar-detail", kwargs={"pk": supplier_car.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["price"] == str(supplier_car.price)

    def test_filter_supplier_cars_by_supplier(self, authenticated_client, supplier, supplier_car):
        url = reverse("suppliercar-list")
        response = authenticated_client.get(url, {"supplier": supplier.id})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_best_prices_endpoint(self, authenticated_client, supplier_car):
        url = reverse("suppliercar-best-prices")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestSupplierDiscountAPI:

    def test_list_supplier_discounts(self, admin_client, supplier_discount):
        url = reverse("supplierdiscount-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_supplier_discount(self, admin_client, supplier_discount):
        url = reverse("supplierdiscount-detail", kwargs={"pk": supplier_discount.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["discount_percent"] == str(supplier_discount.discount_percent)

    def test_create_supplier_discount_as_admin(self, admin_client, supplier, dealership):
        url = reverse("supplierdiscount-list")
        data = {"supplier": supplier.id, "dealership": dealership.id, "discount_percent": "8.00", "min_purchases": 12}

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
