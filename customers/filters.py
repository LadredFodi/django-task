import django_filters
from customers.models import Customer, Sale


class CustomerFilter(django_filters.FilterSet):

    username = django_filters.CharFilter(field_name='user__username', lookup_expr='icontains')
    email = django_filters.CharFilter(field_name='user__email', lookup_expr='icontains')
    country = django_filters.CharFilter()
    city = django_filters.CharFilter(lookup_expr='icontains')
    customer_type = django_filters.ChoiceFilter(choices=Customer._meta.get_field('customer_type').choices)
    email_verified = django_filters.BooleanFilter()
    total_purchases_min = django_filters.NumberFilter(field_name='total_purchases', lookup_expr='gte')
    total_spent_min = django_filters.NumberFilter(field_name='total_spent', lookup_expr='gte')
    loyalty_points_min = django_filters.NumberFilter(field_name='loyalty_points', lookup_expr='gte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Customer
        fields = ['country', 'city', 'customer_type', 'email_verified', 'is_active']


class SaleFilter(django_filters.FilterSet):

    dealership = django_filters.NumberFilter()
    customer = django_filters.NumberFilter()
    car_model = django_filters.NumberFilter()
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    has_discount = django_filters.BooleanFilter(method='filter_has_discount')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Sale
        fields = ['dealership', 'customer', 'car_model', 'is_active']
    
    def filter_has_discount(self, queryset, name, value):

        if value:
            return queryset.filter(discount_applied__gt=0)
        return queryset.filter(discount_applied=0)

