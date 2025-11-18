from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from promotions.models import Promotion, PromotionDealership
from promotions.services import PromotionDealershipService, PromotionService, PromotionSupplierService


@pytest.mark.django_db
class TestPromotionModel:

    def test_create_promotion(self, promotion):
        assert promotion.pk is not None
        assert promotion.name == "Summer Sale"
        assert promotion.default_discount_percent == Decimal("15.00")
        assert promotion.is_active is True

    def test_promotion_str(self, promotion):
        expected = f"{promotion.name} ({promotion.start_date.date()} - {promotion.end_date.date()})"
        assert str(promotion) == expected

    def test_promotion_date_range(self, promotion):
        assert promotion.start_date < promotion.end_date
        assert promotion.start_date <= timezone.now()
        assert promotion.end_date >= timezone.now()

    def test_promotion_type_choices(self, db):
        now = timezone.now()
        valid_types = ["seasonal", "clearance", "holiday", "loyalty", "special"]

        for promo_type in valid_types:
            promo = Promotion.objects.create(
                name=f"Test {promo_type}",
                description="Test",
                promotion_type=promo_type,
                start_date=now,
                end_date=now + timedelta(days=30),
                default_discount_percent=Decimal("10.00"),
            )
            assert promo.promotion_type == promo_type


@pytest.mark.django_db
class TestPromotionDealershipModel:

    def test_create_promotion_dealership(self, promotion_dealership):
        assert promotion_dealership.pk is not None
        assert promotion_dealership.discount_percent == Decimal("15.00")
        assert promotion_dealership.times_applied == 0

    def test_promotion_dealership_str(self, promotion_dealership):
        expected = (
            f"{promotion_dealership.promotion.name} → "
            f"{promotion_dealership.dealership.name} ({promotion_dealership.discount_percent}%)"
        )
        assert str(promotion_dealership) == expected

    def test_promotion_dealership_unique_together(self, promotion, dealership, db):
        PromotionDealership.objects.create(
            promotion=promotion, dealership=dealership, discount_percent=Decimal("15.00")
        )

        with pytest.raises(IntegrityError):
            PromotionDealership.objects.create(
                promotion=promotion, dealership=dealership, discount_percent=Decimal("20.00")
            )


@pytest.mark.django_db
class TestPromotionSupplierModel:

    def test_create_promotion_supplier(self, promotion_supplier):
        assert promotion_supplier.pk is not None
        assert promotion_supplier.discount_percent == Decimal("10.00")
        assert promotion_supplier.times_applied == 0

    def test_promotion_supplier_str(self, promotion_supplier):
        expected = (
            f"{promotion_supplier.promotion.name} → "
            f"{promotion_supplier.supplier.name} ({promotion_supplier.discount_percent}%)"
        )
        assert str(promotion_supplier) == expected


@pytest.mark.django_db
class TestPromotionService:

    def test_get_all_active_promotions(self, promotion):
        result = PromotionService.get_all_active_promotions()

        assert promotion in result
        assert all(p.is_active for p in result)

    def test_get_promotion_by_id(self, promotion):
        result = PromotionService.get_promotion_by_id(promotion.id)

        assert result is not None
        assert result.id == promotion.id

    def test_get_active_now_promotions(self, promotion):
        result = PromotionService.get_active_now_promotions()

        assert promotion in result

        now = timezone.now()
        for promo in result:
            assert promo.start_date <= now
            assert promo.end_date >= now

    def test_get_upcoming_promotions(self, db):
        future_start = timezone.now() + timedelta(days=7)
        future_promo = Promotion.objects.create(
            name="Future Sale",
            description="Coming soon",
            promotion_type="special",
            start_date=future_start,
            end_date=future_start + timedelta(days=14),
            default_discount_percent=Decimal("20.00"),
        )

        result = PromotionService.get_upcoming_promotions()

        assert future_promo in result
        for promo in result:
            assert promo.start_date > timezone.now()

    def test_create_promotion(self, db, car_model):
        now = timezone.now()
        data = {
            "name": "New Year Sale",
            "description": "Special discount",
            "promotion_type": "holiday",
            "start_date": now,
            "end_date": now + timedelta(days=30),
            "default_discount_percent": Decimal("25.00"),
            "car_models": [car_model.id],
        }

        promotion = PromotionService.create_promotion(data)

        assert promotion.pk is not None
        assert promotion.name == "New Year Sale"
        assert promotion.car_models.count() == 1

    def test_update_promotion(self, promotion, car_model):
        data = {"default_discount_percent": Decimal("20.00"), "car_models": [car_model.id]}

        updated = PromotionService.update_promotion(promotion, data)

        assert updated.default_discount_percent == Decimal("20.00")
        assert updated.car_models.count() == 1

    def test_get_promotion_statistics(self, promotion, promotion_dealership, promotion_supplier):
        stats = PromotionService.get_promotion_statistics(promotion)

        assert "times_used" in stats
        assert "car_models_count" in stats
        assert "dealerships" in stats
        assert "suppliers" in stats
        assert "usage" in stats

    def test_check_applicable_valid(self, promotion):
        result = PromotionService.check_applicable(promotion)

        assert result is True

    def test_check_applicable_expired(self, db):
        past_promo = Promotion.objects.create(
            name="Expired Sale",
            description="Old promo",
            promotion_type="special",
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() - timedelta(days=1),
            default_discount_percent=Decimal("15.00"),
        )

        result = PromotionService.check_applicable(past_promo)

        assert result is False

    def test_check_applicable_with_car_model(self, promotion, car_model):
        promotion.car_models.add(car_model)

        result = PromotionService.check_applicable(promotion, car_model_id=car_model.id)
        assert result is True

        result = PromotionService.check_applicable(promotion, car_model_id=99999)
        assert result is False

    def test_check_applicable_with_min_amount(self, promotion):
        promotion.min_purchase_amount = Decimal("10000.00")
        promotion.save()

        result = PromotionService.check_applicable(promotion, amount=Decimal("15000.00"))
        assert result is True

        result = PromotionService.check_applicable(promotion, amount=Decimal("5000.00"))
        assert result is False


@pytest.mark.django_db
class TestPromotionDealershipService:

    def test_get_all_active_dealership_promotions(self, promotion_dealership):
        result = PromotionDealershipService.get_all_active_dealership_promotions()

        assert promotion_dealership in result

    def test_get_dealership_promotions_by_dealership(self, dealership, promotion_dealership):
        result = PromotionDealershipService.get_dealership_promotions_by_dealership(dealership.id)

        assert promotion_dealership in result
        assert all(pd.dealership == dealership for pd in result)

    def test_check_exists(self, promotion, dealership, promotion_dealership):
        result = PromotionDealershipService.check_exists(promotion.id, dealership.id)

        assert result is True

    def test_create_dealership_promotion(self, promotion, dealership_factory):
        new_dealership = dealership_factory()
        data = {"promotion": promotion, "dealership": new_dealership, "discount_percent": Decimal("18.00")}

        promo_deal = PromotionDealershipService.create_dealership_promotion(data)

        assert promo_deal.pk is not None
        assert promo_deal.discount_percent == Decimal("18.00")

    def test_update_dealership_promotion(self, promotion_dealership):
        data = {"discount_percent": Decimal("20.00")}

        updated = PromotionDealershipService.update_dealership_promotion(promotion_dealership, data)

        assert updated.discount_percent == Decimal("20.00")

    def test_apply_promotion(self, promotion_dealership, promotion):
        initial_times = promotion_dealership.times_applied
        initial_promo_times = promotion.times_used
        amount = Decimal("30000.00")

        updated = PromotionDealershipService.apply_promotion(promotion_dealership, amount)

        assert updated.times_applied == initial_times + 1
        assert updated.total_discount_amount > 0

        promotion.refresh_from_db()
        assert promotion.times_used == initial_promo_times + 1

    def test_get_top_dealerships(self, promotion_dealership):
        for _ in range(5):
            PromotionDealershipService.apply_promotion(promotion_dealership, Decimal("25000.00"))

        top = PromotionDealershipService.get_top_dealerships(limit=10)

        assert promotion_dealership in top


@pytest.mark.django_db
class TestPromotionSupplierService:

    def test_get_all_active_supplier_promotions(self, promotion_supplier):
        result = PromotionSupplierService.get_all_active_supplier_promotions()

        assert promotion_supplier in result

    def test_get_supplier_promotions_by_supplier(self, supplier, promotion_supplier):
        result = PromotionSupplierService.get_supplier_promotions_by_supplier(supplier.id)

        assert promotion_supplier in result
        assert all(ps.supplier == supplier for ps in result)

    def test_check_exists(self, promotion, supplier, promotion_supplier):
        result = PromotionSupplierService.check_exists(promotion.id, supplier.id)

        assert result is True

    def test_create_supplier_promotion(self, promotion, supplier_factory):
        new_supplier = supplier_factory()
        data = {"promotion": promotion, "supplier": new_supplier, "discount_percent": Decimal("12.00")}

        promo_supp = PromotionSupplierService.create_supplier_promotion(data)

        assert promo_supp.pk is not None
        assert promo_supp.discount_percent == Decimal("12.00")

    def test_apply_promotion(self, promotion_supplier, promotion):
        initial_times = promotion_supplier.times_applied
        amount = Decimal("100000.00")

        updated = PromotionSupplierService.apply_promotion(promotion_supplier, amount)

        assert updated.times_applied == initial_times + 1
        assert updated.total_discount_amount > 0

    def test_get_top_suppliers(self, promotion_supplier):
        for _ in range(3):
            PromotionSupplierService.apply_promotion(promotion_supplier, Decimal("50000.00"))

        top = PromotionSupplierService.get_top_suppliers(limit=10)

        assert promotion_supplier in top


@pytest.mark.django_db
class TestPromotionAPI:

    def test_list_promotions(self, authenticated_client, promotion):
        url = reverse("promotion-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_promotion(self, authenticated_client, promotion):
        url = reverse("promotion-detail", kwargs={"pk": promotion.pk})
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == promotion.name

    def test_create_promotion_as_admin(self, admin_client):
        now = timezone.now()
        url = reverse("promotion-list")
        data = {
            "name": "API Test Promotion",
            "description": "Test promotion",
            "promotion_type": "special",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
            "default_discount_percent": "15.00",
        }

        response = admin_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Promotion.objects.filter(name="API Test Promotion").exists()

    def test_create_promotion_as_regular_user(self, authenticated_client):
        now = timezone.now()
        url = reverse("promotion-list")
        data = {
            "name": "Test",
            "description": "Test",
            "promotion_type": "special",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=30)).isoformat(),
            "default_discount_percent": "10.00",
        }

        response = authenticated_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_active_promotions_endpoint(self, authenticated_client, promotion):
        url = reverse("promotion-active")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_upcoming_promotions_endpoint(self, authenticated_client, db):
        future_start = timezone.now() + timedelta(days=7)
        Promotion.objects.create(
            name="Future Promo",
            description="Coming soon",
            promotion_type="special",
            start_date=future_start,
            end_date=future_start + timedelta(days=14),
            default_discount_percent=Decimal("20.00"),
        )

        url = reverse("promotion-upcoming")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPromotionDealershipAPI:

    def test_list_promotion_dealerships(self, admin_client, promotion_dealership):
        url = reverse("promotiondealership-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_promotion_dealership(self, admin_client, promotion_dealership):
        url = reverse("promotiondealership-detail", kwargs={"pk": promotion_dealership.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["discount_percent"] == str(promotion_dealership.discount_percent)


@pytest.mark.django_db
class TestPromotionSupplierAPI:

    def test_list_promotion_suppliers(self, admin_client, promotion_supplier):
        url = reverse("promotionsupplier-list")
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_retrieve_promotion_supplier(self, admin_client, promotion_supplier):
        url = reverse("promotionsupplier-detail", kwargs={"pk": promotion_supplier.pk})
        response = admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["discount_percent"] == str(promotion_supplier.discount_percent)
