from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from station.models import (TrainType,
                            Station,
                            Route,
                            Train,
                            Crew,
                            Journey,
                            Order)
from station.serializers import (TrainTypeSerializer,
                                 StationSerializer,
                                 RouteListSerializer,
                                 RouteDetailSerializer,
                                 TrainListSerializer,
                                 TrainDetailSerializer,
                                 TrainCreateSerializer,
                                 CrewListSerializer,
                                 CrewDetailSerializer,
                                 JourneyListSerializer,
                                 JourneyDetailSerializer,
                                 JourneyCreateSerializer,
                                 OrderSerializer,
                                 OrderListSerializer, StationImageSerializer)


class TrainTypeViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    queryset = TrainType.objects.all()
    serializer_class = TrainTypeSerializer


class StationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet
):
    queryset = Station.objects.all()

    def get_serializer_class(self):
        if self.action == "upload_image":
            return StationImageSerializer
        return StationSerializer

    @action(
        methods=["POST"],
        detail=True,
        url_path="upload-image",
        permission_classes=[IsAdminUser],
    )
    def upload_image(self, request, pk=None):
        """Endpoint for uploading image to specific station"""
        station = self.get_object()
        serializer = self.get_serializer(station, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related(
        "source", "destination")
    serializer_class = RouteListSerializer

    def get_queryset(self):
        queryset = self.queryset
        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")
        if source:
            queryset = queryset.filter(source__name__icontains=source)

        if destination:
            queryset = queryset.filter(
                destination__name__icontains=destination)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return RouteListSerializer
        return RouteDetailSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="source",
                type=OpenApiTypes.STR,
                description="Filter by Source Station",
                required=False
            ),
            OpenApiParameter(
                name="destination",
                type=OpenApiTypes.STR,
                description="Filter by Destination Station",
                required=False
            )

        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class TrainViewSet(viewsets.ModelViewSet):
    queryset = Train.objects.select_related(
        "train_type")

    def get_serializer_class(self):
        if self.action == "list":
            return TrainListSerializer
        if self.action == "create":
            return TrainCreateSerializer
        return TrainDetailSerializer


class CrewViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    GenericViewSet
):
    queryset = Crew.objects.prefetch_related("journey_set")

    def get_serializer_class(self):
        if self.action == "list":
            return CrewListSerializer
        return CrewDetailSerializer


class JourneyViewSet(viewsets.ModelViewSet):
    queryset = Journey.objects.select_related(
        "train",
        "route"
    ).prefetch_related("crew")

    def get_queryset(self):
        queryset = self.queryset
        date = self.request.query_params.get("date")
        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")

        if source:
            queryset = queryset.filter(route__source__name__icontains=source)

        if destination:
            queryset = queryset.filter(
                route__destination__name__icontains=destination)

        if date:
            queryset = queryset.filter(date=date)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return JourneyListSerializer
        if self.action == "retrieve":
            return JourneyDetailSerializer
        return JourneyCreateSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="source",
                type=OpenApiTypes.STR,
                description="Filter by Source Station name",
                required=False,
            ),
            OpenApiParameter(
                name="destination",
                type=OpenApiTypes.STR,
                description="Filter by Destination Station name",
                required=False,
            ),
            OpenApiParameter(
                name="date",
                type=OpenApiTypes.DATE,
                description="Filter by departure time (YYYY-MM-DD)",
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class OrderViewSet(
    ListModelMixin,
    CreateModelMixin,
    GenericViewSet
):
    queryset = Order.objects.prefetch_related(
        "tickets__journey__train",
        "tickets__journey__route__source",
        "tickets__journey__route__destination",
    )
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if not user.is_authenticated:
            return queryset.none()
        if user.is_staff:
            return queryset
        return queryset.filter(user=user)

    def get_serializer_class(self):
        if self.action == "list":
            return OrderListSerializer

        return OrderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
