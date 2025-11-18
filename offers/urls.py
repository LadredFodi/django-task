from django.urls import include, path
from rest_framework.routers import DefaultRouter

from offers.views import OfferViewSet

router = DefaultRouter()
router.register(r"offers", OfferViewSet, basename="offer")

urlpatterns = [
    path("", include(router.urls)),
]
