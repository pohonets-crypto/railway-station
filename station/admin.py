from django.contrib import admin

from station.models import (Route,
                            TrainType,
                            Station,
                            Train,
                            Crew,
                            Journey,
                            Order,
                            Ticket)


class TicketInLine(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (TicketInLine,)


admin.site.register(Route)
admin.site.register(TrainType)
admin.site.register(Station)
admin.register(Train)
admin.site.register(Crew)
admin.site.register(Journey)
admin.site.register(Ticket)
