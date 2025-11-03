import django_filters
from suppliers.models import Supplier, SupplierCar, SupplierDiscount


class SupplierFilter(django_filters.FilterSet):

    name = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter()
    founded_year_min = django_filters.NumberFilter(field_name='founded_year', lookup_expr='gte')
    founded_year_max = django_filters.NumberFilter(field_name='founded_year', lookup_expr='lte')
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    rating_max = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Supplier
        fields = ['name', 'country', 'is_active']


class SupplierCarFilter(django_filters.FilterSet):
    supplier = django_filters.NumberFilter()
    car_model = django_filters.NumberFilter()
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    available_quantity_min = django_filters.NumberFilter(field_name='available_quantity', lookup_expr='gte')
    delivery_days_max = django_filters.NumberFilter(field_name='delivery_days', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = SupplierCar
        fields = ['supplier', 'car_model', 'is_active']


class SupplierDiscountFilter(django_filters.FilterSet):
    supplier = django_filters.NumberFilter()
    dealership = django_filters.NumberFilter()
    is_applied = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = SupplierDiscount
        fields = ['supplier', 'dealership', 'is_applied', 'is_active']

