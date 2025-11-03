import django_filters
from dealerships.models import Dealership, DealershipPreference, DealershipInventory, Purchase


class DealershipFilter(django_filters.FilterSet):

    name = django_filters.CharFilter(lookup_expr='icontains')
    country = django_filters.CharFilter()
    city = django_filters.CharFilter(lookup_expr='icontains')
    total_sales_min = django_filters.NumberFilter(field_name='total_sales', lookup_expr='gte')
    total_revenue_min = django_filters.NumberFilter(field_name='total_revenue', lookup_expr='gte')
    balance_min = django_filters.NumberFilter(field_name='balance', lookup_expr='gte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Dealership
        fields = ['name', 'country', 'city', 'is_active']


class DealershipPreferenceFilter(django_filters.FilterSet):

    dealership = django_filters.NumberFilter()
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = DealershipPreference
        fields = ['dealership', 'is_active']


class DealershipInventoryFilter(django_filters.FilterSet):

    dealership = django_filters.NumberFilter()
    car_model = django_filters.NumberFilter()
    quantity_min = django_filters.NumberFilter(field_name='quantity', lookup_expr='gte')
    quantity_max = django_filters.NumberFilter(field_name='quantity', lookup_expr='lte')
    selling_price_min = django_filters.NumberFilter(field_name='selling_price', lookup_expr='gte')
    selling_price_max = django_filters.NumberFilter(field_name='selling_price', lookup_expr='lte')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = DealershipInventory
        fields = ['dealership', 'car_model', 'is_active']
    
    def filter_in_stock(self, queryset, name, value):

        if value:
            return queryset.filter(quantity__gt=0)
        return queryset


class PurchaseFilter(django_filters.FilterSet):

    dealership = django_filters.NumberFilter()
    supplier = django_filters.NumberFilter()
    car_model = django_filters.NumberFilter()
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    total_price_min = django_filters.NumberFilter(field_name='total_price', lookup_expr='gte')
    total_price_max = django_filters.NumberFilter(field_name='total_price', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Purchase
        fields = ['dealership', 'supplier', 'car_model', 'is_active']

