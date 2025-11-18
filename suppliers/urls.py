from django.urls import include, path
from rest_framework.routers import DefaultRouter

from suppliers.views import SupplierCarViewSet, SupplierDiscountViewSet, SupplierViewSet

router = DefaultRouter()
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"supplier-cars", SupplierCarViewSet, basename="suppliercar")
router.register(r"supplier-discounts", SupplierDiscountViewSet, basename="supplierdiscount")

urlpatterns = [
    path("", include(router.urls)),
]
