from rest_framework import serializers

from cars.serializers import CarModelListSerializer
from offers.models import Offer
from offers.tasks import process_customer_offer


class OfferSerializer(serializers.ModelSerializer):

    customer_username = serializers.CharField(source="customer.user.username", read_only=True)
    car_model_detail = CarModelListSerializer(source="car_model", read_only=True)
    matched_dealership_name = serializers.CharField(source="matched_dealership.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "customer",
            "customer_username",
            "car_model",
            "car_model_detail",
            "max_price",
            "status",
            "status_display",
            "matched_dealership",
            "matched_dealership_name",
            "matched_price",
            "processed_at",
            "completed_at",
            "expires_at",
            "notes",
            "search_results",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "status",
            "matched_dealership",
            "matched_price",
            "processed_at",
            "completed_at",
            "search_results",
            "created_at",
            "updated_at",
        ]

    def validate_max_price(self, value):

        if value <= 0:
            raise serializers.ValidationError("Maximum price must be greater than zero.")
        return value

    def validate(self, data):

        customer = self.context["request"].user.customer_profile
        max_price = data.get("max_price")

        if max_price and customer.balance < max_price:
            raise serializers.ValidationError(f"Insufficient funds on balance. Available: ${customer.balance}")

        return data


class OfferListSerializer(serializers.ModelSerializer):

    customer_username = serializers.CharField(source="customer.user.username", read_only=True)
    car_brand = serializers.CharField(source="car_model.brand", read_only=True)
    car_model_name = serializers.CharField(source="car_model.model", read_only=True)
    car_year = serializers.IntegerField(source="car_model.year", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Offer
        fields = [
            "id",
            "customer",
            "customer_username",
            "car_model",
            "car_brand",
            "car_model_name",
            "car_year",
            "max_price",
            "status",
            "status_display",
            "matched_dealership",
            "matched_price",
            "created_at",
        ]


class OfferCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Offer
        fields = [
            "car_model",
            "max_price",
            "expires_at",
            "notes",
        ]

    def validate_max_price(self, value):

        if value <= 0:
            raise serializers.ValidationError("Maximum price must be greater than zero.")
        return value

    def validate(self, data):

        request = self.context.get("request")
        if request and hasattr(request.user, "customer_profile"):
            customer = request.user.customer_profile

            if not customer.email_verified:
                raise serializers.ValidationError("To create an offer, you need to confirm your email.")

            max_price = data.get("max_price")
            if customer.balance < max_price:
                raise serializers.ValidationError(f"Insufficient funds on balance. Available: ${customer.balance}")

        return data

    def create(self, validated_data):

        request = self.context.get("request")
        validated_data["customer"] = request.user.customer_profile

        offer = Offer.objects.create(**validated_data)

        process_customer_offer.delay(offer.id)

        return offer
