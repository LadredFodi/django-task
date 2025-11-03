from django.db.models import Count
from typing import Optional, List
from django.db.models import QuerySet
from cars.models import CarModel


class CarModelService:
    
    @staticmethod
    def get_all_active_cars() -> QuerySet[CarModel]:
        return CarModel.objects.filter(is_active=True)
    
    @staticmethod
    def get_car_by_id(car_model_id: int) -> Optional[CarModel]:
        try:
            return CarModel.objects.get(id=car_model_id, is_active=True)
        except CarModel.DoesNotExist:
            return None
    
    @staticmethod
    def create_car_model(data: dict[str, Any]) -> CarModel:
        return CarModel.objects.create(**data)
    
    @staticmethod
    def update_car_model(car_model: CarModel, data: dict[str, Any]) -> CarModel:
        for key, value in data.items():
            setattr(car_model, key, value)
        car_model.save()
        return car_model
    
    @staticmethod
    def soft_delete_car_model(car_model: CarModel) -> None:
        car_model.soft_delete()
    
    @staticmethod
    def restore_car_model(car_model: CarModel) -> CarModel:
        car_model.restore()
        return car_model
    
    @staticmethod
    def get_popular_models(limit: int = 10) -> List[CarModel]:
        return CarModel.objects.filter(is_active=True).annotate(
            sales_count=Count('sales')
        ).filter(sales_count__gt=0).order_by('-sales_count')[:limit]
    
    @staticmethod
    def get_all_brands() -> List[str]:
        return list(
            CarModel.objects.filter(is_active=True)
            .values_list('brand', flat=True)
            .distinct()
            .order_by('brand')
        )
    
    @staticmethod
    def filter_by_criteria(
        brand: Optional[str] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        body_type: Optional[str] = None,
        fuel_type: Optional[str] = None
    ) -> QuerySet[CarModel]:
        queryset = CarModel.objects.filter(is_active=True)
        
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        if year_min:
            queryset = queryset.filter(year__gte=year_min)
        if year_max:
            queryset = queryset.filter(year__lte=year_max)
        if body_type:
            queryset = queryset.filter(body_type=body_type)
        if fuel_type:
            queryset = queryset.filter(fuel_type=fuel_type)
        
        return queryset

