import django_filters
from django.utils import timezone
from promotions.models import Promotion, PromotionDealership, PromotionSupplier


class PromotionFilter(django_filters.FilterSet):

    name = django_filters.CharFilter(lookup_expr='icontains')
    promotion_type = django_filters.ChoiceFilter(choices=Promotion.PROMOTION_TYPE_CHOICES)
    start_date_from = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='gte')
    start_date_to = django_filters.DateTimeFilter(field_name='start_date', lookup_expr='lte')
    end_date_from = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='gte')
    end_date_to = django_filters.DateTimeFilter(field_name='end_date', lookup_expr='lte')
    discount_min = django_filters.NumberFilter(field_name='default_discount_percent', lookup_expr='gte')
    discount_max = django_filters.NumberFilter(field_name='default_discount_percent', lookup_expr='lte')
    is_active_now = django_filters.BooleanFilter(method='filter_active_now')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = Promotion
        fields = ['name', 'promotion_type', 'is_active']
    
    def filter_active_now(self, queryset, name, value):
        now = timezone.now()
        if value:
            return queryset.filter(
                is_active=True,
                start_date__lte=now,
                end_date__gte=now
            )
        return queryset


class PromotionDealershipFilter(django_filters.FilterSet):
    promotion = django_filters.NumberFilter()
    dealership = django_filters.NumberFilter()
    discount_min = django_filters.NumberFilter(field_name='discount_percent', lookup_expr='gte')
    discount_max = django_filters.NumberFilter(field_name='discount_percent', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = PromotionDealership
        fields = ['promotion', 'dealership', 'is_active']


class PromotionSupplierFilter(django_filters.FilterSet):
    promotion = django_filters.NumberFilter()
    supplier = django_filters.NumberFilter()
    discount_min = django_filters.NumberFilter(field_name='discount_percent', lookup_expr='gte')
    discount_max = django_filters.NumberFilter(field_name='discount_percent', lookup_expr='lte')
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        model = PromotionSupplier
        fields = ['promotion', 'supplier', 'is_active']

