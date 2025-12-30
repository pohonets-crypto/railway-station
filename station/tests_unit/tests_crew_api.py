from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import Crew
from station.serializers import CrewListSerializer

CREW_URL = reverse("station:crew-list")


class ModelTests(TestCase):

    def test_crew_str_method(self):
        crew = Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        self.assertEqual(str(crew), f"{crew.first_name} {crew.last_name}")


class UnauthenticatedStationApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(CREW_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedCrewApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="user@test.test",
            password="user12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_crew_list(self):
        Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        Crew.objects.create(
            first_name="Jack",
            last_name="Black",
        )
        response = self.client.get(CREW_URL)
        crews = Crew.objects.all()
        serializer = CrewListSerializer(crews, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_create_crew_by_not_admin_user(self):
        payload = {
            "first_name": "John",
            "last_name": "Smith",
        }
        response = self.client.post(CREW_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_crew_list_count(self):
        Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        Crew.objects.create(
            first_name="Jack",
            last_name="Black",
        )
        response = self.client.get(CREW_URL)

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

    def test_create_crew_by_admin_user(self):
        payload = {
            "first_name": "John",
            "last_name": "Smith",
        }
        response = self.client.post(CREW_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
