from rest_framework import serializers

from cars.serializers import CarModelListSerializer
from dealerships.models import Dealership, DealershipInventory, DealershipPreference, Purchase


class DealershipSerializer(serializers.ModelSerializer):

    country_name = serializers.CharField(source="country.name", read_only=True)
    location_latitude = serializers.SerializerMethodField()
    location_longitude = serializers.SerializerMethodField()

    class Meta:
        model = Dealership
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "city",
            "address",
            "location",
            "location_latitude",
            "location_longitude",
            "email",
            "phone",
            "website",
            "balance",
            "total_sales",
            "total_revenue",
            "total_profit",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_sales", "total_revenue", "total_profit", "created_at", "updated_at"]

    def get_location_latitude(self, obj):
        if obj.location:
            return obj.location.y
        return None

    def get_location_longitude(self, obj):
        if obj.location:
            return obj.location.x
        return None


class DealershipListSerializer(serializers.ModelSerializer):

    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Dealership
        fields = [
            "id",
            "name",
            "country",
            "country_name",
            "city",
            "total_sales",
            "total_revenue",
            "is_active",
        ]


class DealershipPreferenceSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source="dealership.name", read_only=True)

    class Meta:
        model = DealershipPreference
        fields = [
            "id",
            "dealership",
            "dealership_name",
            "preferred_body_types",
            "preferred_fuel_types",
            "preferred_brands",
            "min_price",
            "max_price",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DealershipInventorySerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source="dealership.name", read_only=True)
    car_model_detail = CarModelListSerializer(source="car_model", read_only=True)
    profit_margin = serializers.SerializerMethodField()

    class Meta:
        model = DealershipInventory
        fields = [
            "id",
            "dealership",
            "dealership_name",
            "car_model",
            "car_model_detail",
            "quantity",
            "purchase_price",
            "selling_price",
            "profit_margin",
            "times_sold",
            "last_sale_date",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "times_sold", "last_sale_date", "created_at", "updated_at"]

    def get_profit_margin(self, obj):
        if obj.purchase_price > 0:
            return float(((obj.selling_price - obj.purchase_price) / obj.purchase_price) * 100)
        return 0


class DealershipInventoryListSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source="dealership.name", read_only=True)
    car_brand = serializers.CharField(source="car_model.brand", read_only=True)
    car_model_name = serializers.CharField(source="car_model.model", read_only=True)
    car_year = serializers.IntegerField(source="car_model.year", read_only=True)

    class Meta:
        model = DealershipInventory
        fields = [
            "id",
            "dealership",
            "dealership_name",
            "car_model",
            "car_brand",
            "car_model_name",
            "car_year",
            "quantity",
            "selling_price",
            "is_active",
        ]


class PurchaseSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source="dealership.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    car_model_detail = CarModelListSerializer(source="car_model", read_only=True)
    promotion_name = serializers.CharField(source="promotion_applied.name", read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "dealership",
            "dealership_name",
            "supplier",
            "supplier_name",
            "car_model",
            "car_model_detail",
            "quantity",
            "unit_price",
            "total_price",
            "discount_applied",
            "promotion_applied",
            "promotion_name",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):

        quantity = data.get("quantity")
        unit_price = data.get("unit_price")
        total_price = data.get("total_price")

        if quantity and unit_price:
            expected_total = quantity * unit_price
            if total_price and abs(float(total_price) - float(expected_total)) > 0.01:
                raise serializers.ValidationError("Total price does not match the quantity and unit price.")

        return data


class PurchaseListSerializer(serializers.ModelSerializer):

    dealership_name = serializers.CharField(source="dealership.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    car_brand = serializers.CharField(source="car_model.brand", read_only=True)
    car_model_name = serializers.CharField(source="car_model.model", read_only=True)

    class Meta:
        model = Purchase
        fields = [
            "id",
            "dealership",
            "dealership_name",
            "supplier",
            "supplier_name",
            "car_model",
            "car_brand",
            "car_model_name",
            "quantity",
            "total_price",
            "created_at",
        ]


class DealershipStatisticsSerializer(serializers.Serializer):

    balance = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_sales = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=16, decimal_places=2)

    inventory = serializers.DictField(child=serializers.DecimalField(max_digits=16, decimal_places=2))

    sales = serializers.DictField()

    purchases = serializers.DictField()

    top_selling_models = serializers.ListField(child=serializers.DictField())

    top_customers = serializers.ListField(child=serializers.DictField())

    active_promotions = serializers.ListField(child=serializers.DictField())


class PurchaseStatisticsSerializer(serializers.Serializer):

    total_purchases = serializers.IntegerField()
    total_quantity = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=16, decimal_places=2)
    avg_unit_price = serializers.DecimalField(max_digits=16, decimal_places=2)

    top_suppliers = serializers.ListField(child=serializers.DictField())

    top_car_models = serializers.ListField(child=serializers.DictField())
