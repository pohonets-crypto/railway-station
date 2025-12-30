import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import (Ticket,
                            Station,
                            Route,
                            TrainType,
                            Train,
                            Journey,
                            Order)
from station.serializers import OrderListSerializer


ORDER_URL = reverse("station:order-list")


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


def create_train():
    train_type = TrainType.objects.create(name=f"type-{uuid.uuid4()}")
    return Train.objects.create(
        name=f"train-{uuid.uuid4()}",
        cargo_num=10,
        places_in_cargo=20,
        train_type=train_type,
    )


def sample_journey(**params):

    defaults = {
        "route": create_route(),
        "train": create_train(),
        "departure_time": timezone.now(),
        "arrival_time": timezone.now() + timedelta(hours=5),
    }

    defaults.update(params)
    return Journey.objects.create(**defaults)


def create_user(**params):
    defaults = {
        "email": f"user-{uuid.uuid4()}@test.com",
        "password": "test12345",
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)


def create_order(**params):
    defaults = {
        "created_at": timezone.now(),
        "user": create_user(),
    }
    defaults.update(params)
    return Order.objects.create(**defaults)


def create_ticket(**params):
    defaults = {
        "cargo": 1,
        "seat": 1,
        "journey": sample_journey(),
        "order": create_order(),
    }
    defaults.update(params)
    return Ticket.objects.create(**defaults)


class ModelTest(TestCase):

    def test_ticket_str_method(self):
        ticket = create_ticket()
        self.assertEqual(str(ticket),
                         str(f"{ticket.journey.route.source} "
                             f"- {ticket.journey.route.destination}"))


class UnauthenticatedTicketAndOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(ORDER_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedTicketAndOrderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test12345",
        )
        self.client.force_authenticate(self.user)

    def test_order_list(self):
        order_1 = create_order(user=self.user)
        Ticket.objects.create(
            order=order_1,
            cargo=10,
            seat=1,
            journey=sample_journey(),
        )
        Ticket.objects.create(
            order=order_1,
            journey=sample_journey(),
            cargo=10,
            seat=2)

        response = self.client.get(ORDER_URL)
        orders = Order.objects.all()
        serializer = OrderListSerializer(orders, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_create_order_by_not_admin_user(self):
        payload = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": 1,
                    "journey": sample_journey().id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["tickets"][0]["cargo"], 1)

    # def test_order_retrieve(self):
    #     order_1 = create_order(user=self.user)
    #     Ticket.objects.create(
    #         order=order_1,
    #         cargo=10,
    #         seat=1,
    #         journey=sample_journey(),
    #     )
    #     url = reverse("station:order-detail", kwargs={"pk": order_1.pk})
    #     response = self.client.get(url)
    #     serializer = OrderSerializer(order_1)
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(response.data, serializer.data)

    def test_create_ticket_with_not_valid_cargo(self):
        payload = {
            "tickets": [
                {
                    "cargo": -1,
                    "seat": 1,
                    "journey": sample_journey().id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cargo", response.data["tickets"][0])
        self.assertEqual(
            response.data["tickets"][0]["cargo"][0].code,
            "min_value"
        )

    def test_create_ticket_with_not_valid_seat(self):
        payload = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": -1,
                    "journey": sample_journey().id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seat", response.data["tickets"][0])
        self.assertEqual(
            response.data["tickets"][0]["seat"][0].code,
            "min_value"
        )

    def test_create_ticket_with_not_existing_cargo(self):
        payload = {
            "tickets": [
                {
                    "cargo": 100,
                    "seat": 1,
                    "journey": sample_journey().id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cargo", response.data["tickets"][0])
        self.assertEqual(
            response.data["tickets"][0]["cargo"][0].code,
            "invalid"
        )

    def test_create_ticket_with_not_existing_seat(self):
        payload = {
            "tickets": [
                {
                    "cargo": 1,
                    "seat": 100,
                    "journey": sample_journey().id,
                }
            ]
        }
        response = self.client.post(ORDER_URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seat", response.data["tickets"][0])
        self.assertEqual(
            response.data["tickets"][0]["seat"][0].code,
            "invalid"
        )
