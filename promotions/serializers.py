"""Serializers for promotion models."""

from django.utils import timezone
from rest_framework import serializers

from cars.serializers import CarModelListSerializer
from promotions.models import Promotion, PromotionDealership, PromotionSupplier
from promotions.services import PromotionDealershipService, PromotionSupplierService


class PromotionSerializer(serializers.ModelSerializer):
    promotion_type_display = serializers.CharField(source="get_promotion_type_display", read_only=True)
    car_models_detail = CarModelListSerializer(source="car_models", many=True, read_only=True)
    is_active_now = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "description",
            "promotion_type",
            "promotion_type_display",
            "start_date",
            "end_date",
            "default_discount_percent",
            "car_models",
            "car_models_detail",
            "min_purchase_amount",
            "times_used",
            "is_active_now",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_used", "created_at", "updated_at"]

    def get_is_active_now(self, obj):
        now = timezone.now()
        return obj.is_active and obj.start_date <= now <= obj.end_date

    def validate(self, data):
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("Start date must be before end date.")

        return data


class PromotionListSerializer(serializers.ModelSerializer):
    promotion_type_display = serializers.CharField(source="get_promotion_type_display", read_only=True)
    is_active_now = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "promotion_type",
            "promotion_type_display",
            "start_date",
            "end_date",
            "default_discount_percent",
            "times_used",
            "is_active_now",
            "is_active",
        ]

    def get_is_active_now(self, obj):
        now = timezone.now()
        return obj.is_active and obj.start_date <= now <= obj.end_date


class PromotionDealershipSerializer(serializers.ModelSerializer):
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    dealership_name = serializers.CharField(source="dealership.name", read_only=True)

    class Meta:
        model = PromotionDealership
        fields = [
            "id",
            "promotion",
            "promotion_name",
            "dealership",
            "dealership_name",
            "discount_percent",
            "times_applied",
            "total_discount_amount",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_applied", "total_discount_amount", "created_at", "updated_at"]

    def validate(self, data):
        promotion = data.get("promotion")
        dealership = data.get("dealership")

        if not self.instance:
            if PromotionDealershipService.check_exists(promotion.id, dealership.id):
                raise serializers.ValidationError("This promotion-dealership relationship already exists.")

        return data


class PromotionSupplierSerializer(serializers.ModelSerializer):
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = PromotionSupplier
        fields = [
            "id",
            "promotion",
            "promotion_name",
            "supplier",
            "supplier_name",
            "discount_percent",
            "times_applied",
            "total_discount_amount",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_applied", "total_discount_amount", "created_at", "updated_at"]

    def validate(self, data):
        promotion = data.get("promotion")
        supplier = data.get("supplier")

        if not self.instance:
            if PromotionSupplierService.check_exists(promotion.id, supplier.id):
                raise serializers.ValidationError("This promotion-supplier relationship already exists.")

        return data
