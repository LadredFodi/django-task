from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers.views import CustomerViewSet, SaleViewSet

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'sales', SaleViewSet, basename='sale')

urlpatterns = [
    path('', include(router.urls)),
]

