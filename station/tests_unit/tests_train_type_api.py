from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status

from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import TrainType
from station.serializers import TrainTypeSerializer


TRAIN_TYPE_URL = reverse("station:traintype-list")


def create_train_type(**params):
    return TrainType.objects.create(**params)


class ModelTest(TestCase):

    def test_train_type_str(self):
        train_type = create_train_type()

        self.assertEqual(str(train_type), train_type.name)


class UnauthenticatedTrainTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(TRAIN_TYPE_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainTypeApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin",
            password="admin12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_train_type_list(self):
        create_train_type(name="Test Station")

        response = self.client.get(TRAIN_TYPE_URL)

        train_types = TrainType.objects.all()

        serializer = TrainTypeSerializer(train_types, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_create_train_type_by_not_admin_user(self):
        payload = {
            "name": "test1",
        }
        response = self.client.post(TRAIN_TYPE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_train_type_list_count(self):
        create_train_type(name="Type A")
        create_train_type(name="Type B")

        response = self.client.get(TRAIN_TYPE_URL)

        self.assertEqual(len(response.data["results"]), 2)


class AdminTrainTypeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="admin12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_train_type_by_admin_user(self):
        payload = {
            "name": "test1",
        }
        response = self.client.post(TRAIN_TYPE_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
