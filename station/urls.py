from django.urls import path, include
from rest_framework import routers

from station.views import (TrainTypeViewSet,
                           StationViewSet,
                           RouteViewSet,
                           TrainViewSet,
                           CrewViewSet,
                           JourneyViewSet,
                           OrderViewSet)

router = routers.DefaultRouter()
router.register("train_types", TrainTypeViewSet)
router.register("stations", StationViewSet)
router.register("routes", RouteViewSet)
router.register("trains", TrainViewSet)
router.register("crews", CrewViewSet)
router.register("journeys", JourneyViewSet)
router.register("orders", OrderViewSet, basename="order")
urlpatterns = []
urlpatterns = [path("", include(router.urls))]

app_name = "station"
