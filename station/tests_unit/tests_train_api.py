from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import TrainType, Train
from station.serializers import (TrainListSerializer,
                                 TrainDetailSerializer,
                                 TrainCreateSerializer)


TRAIN_URL = reverse("station:train-list")


def train_detail_url(train_id):
    return reverse("station:train-detail", args=[train_id])


def create_train_type(**params):
    return TrainType.objects.create(**params)


def create_train(**params):
    defaults = {
        "name": "Test",
        "cargo_num": 10,
        "places_in_cargo": 20,
        "train_type": create_train_type(name="Test"),
    }
    defaults.update(params)
    return Train.objects.create(**defaults)


class ModelTest(TestCase):

    def test_train_str(self):
        train = create_train()
        self.assertEqual(str(train), train.name)


class UnauthenticatedTrainApiTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(TRAIN_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTrainApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="user12345",
        )
        self.client.force_authenticate(user=self.user)

    def test_trains_list(self):
        create_train()
        create_train(name="Test1")
        response = self.client.get(TRAIN_URL)
        trains = Train.objects.all()
        serializer = TrainListSerializer(trains, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_train_retrieve(self):
        train = create_train()
        response = self.client.get(train_detail_url(train.id))
        serializer = TrainDetailSerializer(train)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer.data, response.data)

    def test_create_train_by_not_admin_user(self):
        payload = {
            "name": "Test2",
            "cargo_num": 10,
            "places_in_cargo": 20,
            "train_type": create_train_type(name="Test2").id,
        }
        response = self.client.post(TRAIN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminJourneyTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="test12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_train_by_admin(self):
        payload = {
            "name": "Test2",
            "cargo_num": 10,
            "places_in_cargo": 20,
            "train_type": create_train_type(name="Test2").id,
        }
        response = self.client.post(TRAIN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_train_with_cargo_num_less_than_zero(self):
        payload = {
            "name": "Test2",
            "cargo_num": -10,
            "places_in_cargo": 20,
            "train_type": create_train_type(name="Test2").id,
        }
        response = self.client.post(TRAIN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cargo_num", response.data)

    def test_create_train_with_places_in_cargo_less_than_zero(self):
        payload = {
            "name": "Test2",
            "cargo_num": 10,
            "places_in_cargo": -20,
            "train_type": create_train_type(name="Test2").id,
        }
        response = self.client.post(TRAIN_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("places_in_cargo", response.data)

    def test_serializer_valid_data(self):
        train_type = create_train_type(name="Test2").pk
        payload = {
            "name": "Test2",
            "cargo_num": 10,
            "places_in_cargo": 20,
            "train_type": train_type,
        }
        serializer = TrainCreateSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        train = serializer.save()

        self.assertEqual(train.train_type.id, train_type)
        self.assertEqual(train.cargo_num, payload["cargo_num"])
        self.assertEqual(train.places_in_cargo, payload["places_in_cargo"])
        self.assertEqual(train.name, payload["name"])
