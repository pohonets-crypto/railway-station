import pathlib
import uuid

from django.core.validators import MinValueValidator
from django.db import models
from rest_framework.exceptions import ValidationError
from django.utils.text import slugify

from railway_station import settings


class TrainType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=100)
    cargo_num = models.IntegerField(
        validators=[
            MinValueValidator(1),
        ]
    )
    places_in_cargo = models.IntegerField(
        validators=[MinValueValidator(1)]
    )
    train_type = models.ForeignKey(
        TrainType, on_delete=models.PROTECT)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Trains"


def station_image_path(instance: "Station", filename: str) -> str:
    filename = (f"{slugify(instance.name)}-{uuid.uuid4()}"
                + pathlib.Path(filename).suffix)
    return str(pathlib.Path("uploads") / "station" / filename)


class Station(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image = models.ImageField(
        null=True, upload_to=station_image_path)

    def __str__(self):
        return self.name


class Route(models.Model):
    source = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        related_name="routes_from",
    )
    destination = models.ForeignKey(
        Station,
        on_delete=models.SET_NULL,
        null=True,
        related_name="routes_to",
    )
    distance = models.IntegerField(
        validators=[
            MinValueValidator(1, message="Must be positive.")
        ]
    )

    def clean(self):
        if self.source == self.destination:
            raise ValidationError(
                "Source and destination must be different."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        source = self.source.name if self.source else "?"
        dest = self.destination.name if self.destination else "?"
        return f"{source} - {dest}"


class Crew(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Journey(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.PROTECT,
        related_name="journeys",
    )
    train = models.ForeignKey(
        Train,
        on_delete=models.PROTECT,
        related_name="journeys",
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, blank=True)

    def clean(self):
        if self.departure_time >= self.arrival_time:
            raise ValidationError(
                "Departure time must be earlier than Arrival time")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.route.source.name} - {self.route.destination.name}"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    def __str__(self):
        return str(self.created_at)

    class Meta:
        ordering = ["-created_at"]


class Ticket(models.Model):
    cargo = models.IntegerField(
        validators=[
            MinValueValidator(
                1, message="Cargo must be at least 1"),
        ]
    )
    seat = models.IntegerField(
        validators=[
            MinValueValidator(
                1, message="Seat must be at least 1"),
        ]
    )
    journey = models.ForeignKey(
        Journey,
        on_delete=models.CASCADE,
        null=False,
        related_name="tickets"
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        null=False,
        related_name="tickets"
    )

    @staticmethod
    def validate_ticket(cargo, seat, journey, error_to_raise):
        if journey is None:
            raise error_to_raise({"journey": "Journey must be set"})

        train = journey.train
        if train is None:
            raise error_to_raise({"train": "Journey must have a train"})

        if not (1 <= cargo <= train.cargo_num):
            raise error_to_raise(
                {
                    "cargo": (
                        f"Cargo number must be in range "
                        f"[1, {train.cargo_num}]"
                    )
                }
            )

        if not (1 <= seat <= train.places_in_cargo):
            raise error_to_raise(
                {
                    "seat": (
                        f"Seat number must be in range "
                        f"[1, {train.places_in_cargo}]"
                    )
                }
            )

        if Ticket.objects.filter(
            journey=journey,
            cargo=cargo,
            seat=seat
        ).exists():
            raise error_to_raise(
                {"seat": "This seat is already taken"}
            )

    def clean(self):
        Ticket.validate_ticket(
            self.cargo,
            self.seat,
            self.journey,
            ValidationError,
        )

    def save(
            self,
            *args,
            force_insert=False,
            force_update=False,
            using=None,
            update_fields=None,
    ):
        self.full_clean()
        return super(Ticket, self).save(
            force_insert, force_update, using, update_fields
        )

    def __str__(self):
        return (f"{self.journey.route.source} "
                f"- {self.journey.route.destination}") \
            if self.journey else f"Ticket {self.pk or ''}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["journey", "cargo", "seat"],
                name="unique_seat_per_journey"
            )
        ]
        ordering = ["cargo", "seat"]
