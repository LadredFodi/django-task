from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dealerships.views import (
    DealershipViewSet,
    DealershipPreferenceViewSet,
    DealershipInventoryViewSet,
    PurchaseViewSet
)

router = DefaultRouter()
router.register(r'dealerships', DealershipViewSet, basename='dealership')
router.register(r'preferences', DealershipPreferenceViewSet, basename='dealershippreference')
router.register(r'inventory', DealershipInventoryViewSet, basename='dealershipinventory')
router.register(r'purchases', PurchaseViewSet, basename='purchase')

urlpatterns = [
    path('', include(router.urls)),
]

