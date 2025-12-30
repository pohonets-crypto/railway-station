from django.db import transaction
from rest_framework import serializers

from station.models import (TrainType,
                            Station,
                            Route,
                            Train,
                            Crew,
                            Journey,
                            Ticket,
                            Order)


class TrainTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainType
        fields = ("id", "name")


class StationImageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Station
        fields = ("id", "image")


class StationSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)
    class Meta:
        model = Station
        fields = ("id", "name", "latitude", "longitude", "image")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(serializers.ModelSerializer):
    source_station = serializers.CharField(
        source="source.name", read_only=True)
    destination_station = serializers.CharField(
        source="destination.name", read_only=True)
    station_source_image = serializers.ImageField(
        source="source.image", read_only=True)
    station_destination_image = serializers.ImageField(
        source="destination.image", read_only=True)

    class Meta:
        model = Route
        fields = (
            "id",
            "source_station",
            "station_source_image",
            "destination_station",
            "station_destination_image",
            "distance"
        )


class RouteDetailSerializer(RouteSerializer):

    class Meta:
        model = Route
        fields = (
            "id",
            "source",
            "destination",
            "distance"
        )

    def validate(self, attrs):
        source = attrs.get("source")
        destination = attrs.get("destination")

        if source == destination:
            raise serializers.ValidationError({
                "destination": "Source and destination must be different."
            })
        return attrs


class TrainListSerializer(serializers.ModelSerializer):
    train_type = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "train_type"
        )


class TrainDetailSerializer(serializers.ModelSerializer):
    train_type = TrainTypeSerializer(many=False, read_only=True)

    class Meta:
        model = Train
        fields = (
            "id",
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type"
        )


class TrainCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Train
        fields = (
            "name",
            "cargo_num",
            "places_in_cargo",
            "train_type"
        )


class CrewDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = (
            "id", "first_name", "last_name",
        )


class CrewListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Crew
        fields = ("id", "full_name",)


class JourneyListSerializer(serializers.ModelSerializer):
    route = serializers.SerializerMethodField()
    train = serializers.SlugRelatedField(
        read_only=True, slug_field="name")
    crew = CrewDetailSerializer(many=True, read_only=True)
    tickets_available = serializers.SerializerMethodField()

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew",
            "tickets_available"
        )

    def get_route(self, obj):
        if obj.route:
            return f"{obj.route.source} - {obj.route.destination}"
        return None

    def get_tickets_available(self, obj):
        all_seats = obj.train.cargo_num * obj.train.places_in_cargo
        taken_seats = obj.tickets.count()
        return all_seats - taken_seats


class JourneyCreateSerializer(serializers.ModelSerializer):
    crew = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Crew.objects.all(),
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew"
        )

    def validate(self, attrs):
        departure_time = attrs.get(
            "departure_time", getattr(
                self.instance, "departure_time", None))
        arrival_time = attrs.get(
            "arrival_time", getattr(
                self.instance, "arrival_time", None))
        if departure_time and arrival_time and arrival_time <= departure_time:
            raise serializers.ValidationError({
                "departure_time":
                    "Departure time must be earlier than arrival time."
            })
        return attrs


class TicketSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        Ticket.validate_ticket(
            attrs["cargo"],
            attrs["seat"],
            attrs["journey"],
            serializers.ValidationError,
        )
        return attrs

    class Meta:
        model = Ticket
        fields = ("id", "cargo", "seat", "journey")


class TicketListSerializer(TicketSerializer):
    journey = JourneyListSerializer(read_only=True)


class TicketSeatsSerializer(TicketSerializer):

    class Meta:
        model = Ticket
        fields = ("cargo", "seat")


class JourneyDetailSerializer(serializers.ModelSerializer):
    route = RouteDetailSerializer(read_only=True)
    train = TrainDetailSerializer(read_only=True)
    crew = CrewDetailSerializer(many=True, read_only=True)
    taken_places = TicketSeatsSerializer(
        source="tickets", many=True, read_only=True
    )

    class Meta:
        model = Journey
        fields = (
            "id",
            "route",
            "train",
            "departure_time",
            "arrival_time",
            "crew",
            "taken_places",
        )


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(
        many=True,
    )

    class Meta:
        model = Order
        fields = ("id", "tickets", "created_at")

    def create(self, validated_data):
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets")
            order = Order.objects.create(**validated_data)
            for ticket_data in tickets_data:
                Ticket.objects.create(order=order, **ticket_data)
        return order


class OrderListSerializer(OrderSerializer):
    tickets = TicketListSerializer(many=True, read_only=True)
