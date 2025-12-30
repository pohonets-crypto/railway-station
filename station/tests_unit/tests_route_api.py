import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import Station, Route
from station.serializers import RouteListSerializer, RouteDetailSerializer


ROUTE_URL = reverse("station:route-list")


def create_station(name=None):
    return Station.objects.create(
        name=name or f"station-{uuid.uuid4()}"
    )


def create_route(**params):
    defaults = {
        "source": create_station(),
        "destination": create_station(),
        "distance": 100,
    }
    defaults.update(params)
    return Route.objects.create(**defaults)


class ModelTest(TestCase):

    def test_route_str(self):
        route = create_route()
        self.assertEqual(str(route),
                         f"{route.source.name} - {route.destination.name}")


class UnauthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ROUTE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedRouteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test12345",
        )
        self.client.force_authenticate(self.user)

    def test_routes_list(self):
        create_route()
        create_route(
            source=create_station("london"),
            destination=create_station("paris"),
        )
        response = self.client.get(ROUTE_URL)
        routes = Route.objects.all()
        serializer = RouteListSerializer(routes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

        self.assertIn(serializer.data[0], response.data["results"])
        self.assertIn(serializer.data[1], response.data["results"])

    def test_filter_routes_by_source(self):
        route_kyiv = create_route(source=create_station("kyiv"))
        route_london = create_route(source=create_station("london"))

        response = self.client.get(ROUTE_URL,
                                   {"source": "kyiv"},)
        serializer_kyiv = RouteListSerializer(route_kyiv)
        serializer_london = RouteListSerializer(route_london)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_kyiv.data, response.data["results"])
        self.assertNotIn(serializer_london.data, response.data["results"])

    def test_filter_routes_by_destination(self):
        route_kyiv = create_route(destination=create_station("kyiv"))
        route_london = create_route(destination=create_station("london"))

        response = self.client.get(ROUTE_URL,
                                   {"destination": "kyiv"},)
        serializer_kyiv = RouteListSerializer(route_kyiv)
        serializer_london = RouteListSerializer(route_london)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_kyiv.data, response.data["results"])
        self.assertNotIn(serializer_london.data, response.data["results"])

    def test_create_route_by_not_admin_user(self):
        payload = {
            "source": create_station(),
            "destination": create_station(),
            "distance": 100,
        }
        response = self.client.post(ROUTE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_route_detail(self):
        route = create_route()

        url = reverse("station:route-detail", kwargs={"pk": route.id})
        response = self.client.get(url)
        serializer = RouteDetailSerializer(route)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


class AdminRouteTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="test12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_route_by_admin_user(self):
        payload = {
            "source": create_station(name="london").pk,
            "destination": create_station(name="paris").pk,
            "distance": 100,
        }

        response = self.client.post(ROUTE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["source"], payload["source"])
        self.assertEqual(response.data["destination"], payload["destination"])
        self.assertEqual(response.data["distance"], payload["distance"])

    def test_not_unique_fields_source_and_destination(self):
        station1 = Station.objects.create(name="london")
        payload = {
            "source": station1.pk,
            "destination": station1.pk,
            "distance": 100,
        }
        response = self.client.post(ROUTE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["destination"][0].code,
            "invalid"
        )
