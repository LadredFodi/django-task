import django_filters
from offers.models import Offer


class OfferFilter(django_filters.FilterSet):

    customer = django_filters.NumberFilter()
    car_model = django_filters.NumberFilter()
    status = django_filters.ChoiceFilter(choices=Offer.STATUS_CHOICES)
    matched_dealership = django_filters.NumberFilter()
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    max_price_min = django_filters.NumberFilter(field_name='max_price', lookup_expr='gte')
    max_price_max = django_filters.NumberFilter(field_name='max_price', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Offer
        fields = ['customer', 'car_model', 'status', 'matched_dealership', 'is_active']

