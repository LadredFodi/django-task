from django.urls import path, include
from rest_framework.routers import DefaultRouter
from suppliers.views import SupplierViewSet, SupplierCarViewSet, SupplierDiscountViewSet

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'supplier-cars', SupplierCarViewSet, basename='suppliercar')
router.register(r'supplier-discounts', SupplierDiscountViewSet, basename='supplierdiscount')

urlpatterns = [
    path('', include(router.urls)),
]

