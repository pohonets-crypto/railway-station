from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import Station
from station.serializers import StationSerializer


def create_station(**params):
    return Station.objects.create(**params)

STATION_URL = reverse("station:station-list")

class ModelTest(TestCase):

    def test_station_str(self):
        station = create_station()
        self.assertEqual(str(station), station.name)


class UnauthenticatedStationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(STATION_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedStationApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.test",
            password="user12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_station_list(self):
        create_station(name="test")
        response = self.client.get(STATION_URL)
        stations = Station.objects.all()
        serializer = StationSerializer(stations, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_create_station_by_not_admin_user(self):
        payload = {
            "name": "Test Station",
        }
        response = self.client.post(STATION_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_station_list_count(self):
        create_station(name="test1")
        create_station(name="test2")
        response = self.client.get(STATION_URL)

        self.assertEqual(len(response.data["results"]), 2)


class AdminStationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="admin12345",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_station_by_admin_user(self):
        payload = {
            "name": "Test Station",
        }
        response = self.client.post(STATION_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)