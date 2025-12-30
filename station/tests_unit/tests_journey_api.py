import uuid
from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse

from rest_framework.test import APIClient

from station.models import Journey, Route, Train, Crew, Station, TrainType
from station.serializers import JourneyListSerializer, JourneyDetailSerializer, JourneyCreateSerializer

JOURNEY_URL = reverse("station:journey-list")

def journey_detail_url(journey_id):
    return reverse("station:journey-detail", args=[journey_id])

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


class ModelTest(TestCase):

    def test_journey_str(self):
        journey = sample_journey()
        self.assertEqual(str(journey),
                         f"{journey.route.source.name} - {journey.route.destination.name}")


class UnauthenticatedJourneyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(JOURNEY_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedJourneyApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="test@test.test",
            password="test12345",
        )
        self.client.force_authenticate(self.user)

    def test_journeys_list(self):
        route = create_route(
            source=create_station(name="station1"),
            destination=create_station(name="station2"),
        )

        sample_journey()
        journey_with_crew = sample_journey(
            route=route,
        )

        crew_1 = Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        crew_2 = Crew.objects.create(
            first_name="Jack",
            last_name="Black",
        )

        journey_with_crew.crew.add(crew_1, crew_2)

        response = self.client.get(JOURNEY_URL)

        journeys = Journey.objects.all()
        serializer = JourneyListSerializer(journeys, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], serializer.data)

    def test_filter_journeys_by_source(self):
        kyiv = Station.objects.create(name="Kyiv")
        odesa = Station.objects.create(name="Odesa")

        route_kyiv = create_route(source=kyiv)
        route_odesa = create_route(source=odesa)

        journey_1 = sample_journey(route=route_kyiv)
        journey_2 = sample_journey(route=route_odesa)

        response = self.client.get(
            JOURNEY_URL,
            {"source": "Kyiv"},
        )

        serializer_kyiv = JourneyListSerializer(journey_1)
        serializer_odesa = JourneyListSerializer(journey_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_kyiv.data, response.data["results"])
        self.assertNotIn(serializer_odesa.data, response.data["results"])

    def test_filter_journeys_by_destination(self):
        kyiv = Station.objects.create(name="Kyiv")
        odesa = Station.objects.create(name="Odesa")

        route_kyiv = create_route(destination=kyiv)
        route_odesa = create_route(destination=odesa)

        journey_1 = sample_journey(route=route_kyiv)
        journey_2 = sample_journey(route=route_odesa)

        response = self.client.get(
            JOURNEY_URL,
            {"destination": "Kyiv"},
        )
        serializer_kyiv = JourneyListSerializer(journey_1)
        serializer_odesa = JourneyListSerializer(journey_2)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_kyiv.data, response.data["results"])
        self.assertNotIn(serializer_odesa.data, response.data["results"])

    def test_create_journey_by_not_admin_user(self):
        payload = {
                "arrival_time": timezone.now() + timedelta(hours=5),
                "departure_time": timezone.now(),
                "route": create_route().pk,
                "train": create_train().pk,
            }

        response = self.client.post(JOURNEY_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_journey_detail(self):
        journey = sample_journey()

        url = journey_detail_url(journey.pk)
        response = self.client.get(url)
        serializer = JourneyDetailSerializer(journey)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)


class AdminJourneyTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="admin@test.test",
            password="test12345",
            is_staff=True,
        )
        self.client.force_authenticate(self.user)

    def test_create_journey_by_admin(self):
        payload = {
            "route": create_route().pk,
            "train": create_train().pk,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=5),
        }

        response = self.client.post(JOURNEY_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_journey_by_admin_with_crew(self):
        crew_1 = Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        crew_2 = Crew.objects.create(
            first_name="Jack",
            last_name="Black",
        )
        payload = {
            "route": create_route().pk,
            "train": create_train().pk,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=5),
            "crew": [crew_1.pk, crew_2.pk],
        }

        response = self.client.post(JOURNEY_URL, payload)

        journey = Journey.objects.get(id=response.data["id"])

        crew = journey.crew.all()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn(crew_1, crew)
        self.assertIn(crew_2, crew)
        self.assertEqual(crew.count(), 2)

    def test_arrival_time_must_be_later_than_departure_time(self):
        payload = {
            "arrival_time": timezone.now(),
            "departure_time": timezone.now() + timedelta(hours=5),
            "route": create_route().pk,
            "train": create_train().pk,
        }

        response = self.client.post(JOURNEY_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "departure_time",
            response.data)

    def test_serializer_valid_data(self):
        crew_1 = Crew.objects.create(
            first_name="John",
            last_name="Smith",
        )
        crew_2 = Crew.objects.create(
            first_name="Jack",
            last_name="Black",
        )
        route = create_route().pk
        train = create_train().pk
        payload = {
            "route": route,
            "train": train,
            "departure_time": timezone.now(),
            "arrival_time": timezone.now() + timedelta(hours=3),
            "crew": [crew_1.id, crew_2.id],
        }

        serializer = JourneyCreateSerializer(data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

        journey = serializer.save()

        self.assertEqual(journey.route.id, route)
        self.assertEqual(journey.train.id, train)
        self.assertEqual(journey.crew.count(), 2)
