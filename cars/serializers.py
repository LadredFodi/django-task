from rest_framework import serializers

from cars.models import CarModel


class CarModelSerializer(serializers.ModelSerializer):

    body_type_display = serializers.CharField(source="get_body_type_display", read_only=True)
    fuel_type_display = serializers.CharField(source="get_fuel_type_display", read_only=True)
    transmission_display = serializers.CharField(source="get_transmission_display", read_only=True)
    drive_type_display = serializers.CharField(source="get_drive_type_display", read_only=True)

    class Meta:
        model = CarModel
        fields = [
            "id",
            "brand",
            "model",
            "year",
            "body_type",
            "body_type_display",
            "color",
            "doors",
            "seats",
            "fuel_type",
            "fuel_type_display",
            "engine_volume",
            "horsepower",
            "transmission",
            "transmission_display",
            "drive_type",
            "drive_type_display",
            "description",
            "vin_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CarModelListSerializer(serializers.ModelSerializer):

    body_type_display = serializers.CharField(source="get_body_type_display", read_only=True)
    fuel_type_display = serializers.CharField(source="get_fuel_type_display", read_only=True)

    class Meta:
        model = CarModel
        fields = [
            "id",
            "brand",
            "model",
            "year",
            "body_type",
            "body_type_display",
            "fuel_type",
            "fuel_type_display",
            "color",
            "engine_volume",
            "horsepower",
            "is_active",
        ]
        read_only_fields = ["id"]
