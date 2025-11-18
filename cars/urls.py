from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cars.views import CarModelViewSet

router = DefaultRouter()
router.register(r"models", CarModelViewSet, basename="carmodel")

urlpatterns = [
    path("", include(router.urls)),
]
