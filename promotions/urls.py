from django.urls import path, include
from rest_framework.routers import DefaultRouter
from promotions.views import PromotionViewSet, PromotionDealershipViewSet, PromotionSupplierViewSet

router = DefaultRouter()
router.register(r'promotions', PromotionViewSet, basename='promotion')
router.register(r'promotion-dealerships', PromotionDealershipViewSet, basename='promotiondealership')
router.register(r'promotion-suppliers', PromotionSupplierViewSet, basename='promotionsupplier')

urlpatterns = [
    path('', include(router.urls)),
]

