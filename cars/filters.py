import django_filters

from cars.models import CarModel


class CarModelFilter(django_filters.FilterSet):

    brand = django_filters.CharFilter(lookup_expr="icontains")
    model = django_filters.CharFilter(lookup_expr="icontains")
    year_min = django_filters.NumberFilter(field_name="year", lookup_expr="gte")
    year_max = django_filters.NumberFilter(field_name="year", lookup_expr="lte")
    body_type = django_filters.ChoiceFilter(choices=CarModel.BODY_TYPE_CHOICES)
    fuel_type = django_filters.ChoiceFilter(choices=CarModel.FUEL_TYPE_CHOICES)
    transmission = django_filters.ChoiceFilter(choices=CarModel.TRANSMISSION_CHOICES)
    drive_type = django_filters.ChoiceFilter(choices=CarModel.DRIVE_TYPE_CHOICES)
    engine_volume_min = django_filters.NumberFilter(field_name="engine_volume", lookup_expr="gte")
    engine_volume_max = django_filters.NumberFilter(field_name="engine_volume", lookup_expr="lte")
    horsepower_min = django_filters.NumberFilter(field_name="horsepower", lookup_expr="gte")
    horsepower_max = django_filters.NumberFilter(field_name="horsepower", lookup_expr="lte")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = CarModel
        fields = [
            "brand",
            "model",
            "year",
            "body_type",
            "fuel_type",
            "transmission",
            "drive_type",
            "color",
            "is_active",
        ]
