from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from rest_framework.exceptions import ValidationError

from railway_station import settings


class TrainType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Train(models.Model):
    name = models.CharField(max_length=100)
    cargo_num = models.IntegerField()
    places_in_cargo = models.IntegerField()
    train_type = models.ForeignKey(
        TrainType, on_delete=models.SET_NULL, null=True)


    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Trains"


class Station(models.Model):
    name = models.CharField(max_length=100, unique=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

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

    def __str__(self):
        return self.source.name


class Crew(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Journey(models.Model):
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        related_name="journeys",
    )
    train = models.ForeignKey(
        Train,
        on_delete=models.SET_NULL,
        null=True,
        related_name="journeys",
    )
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()
    crew = models.ManyToManyField(Crew, blank=True)

    def __str__(self):
        return self.train.name if self.train \
            else f"Journey #{self.pk} (no train)"


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
        Journey, on_delete=models.SET_NULL, null=True
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True
    )

    @staticmethod
    def validate_ticket(cargo, seat, journey, error_to_raise):
        for ticket_attr_value, ticket_attr_name, journey_attr_name in [
            (cargo, "cargo", "cargos"),
            (seat, "seat", "seats_in_cargo"),
        ]:
            if journey is None:
                raise error_to_raise({"journey": "Journey must be set"})
            count_attrs = getattr(journey, journey_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} "
                                          f"number must be in available range: "
                                          f"[1, {journey_attr_name}]: "
                                          f"[1, {count_attrs}]"
                    }
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
        return self.journey.name if self.journey else f"Ticket {self.pk or ''}"

    class Meta:
        unique_together = ("journey", "cargo", "seat")
        ordering = ["cargo", "seat"]



