from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from patients.models import Patient


class HomeVisit(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Solicitada"
        CONFIRMED = "confirmed", "Confirmada"
        ON_ROUTE = "on_route", "En camino"
        COMPLETED = "completed", "Finalizada"
        CANCELED = "canceled", "Cancelada"

    class VisitType(models.TextChoices):
        CLINICAL = "clinical", "Consulta clínica"
        VACCINATION = "vaccination", "Vacunación"
        DELIVERY = "delivery", "Entrega de productos"
        FOLLOW_UP = "follow_up", "Control o seguimiento"
        OTHER = "other", "Otro"

    patient = models.ForeignKey(Patient, verbose_name="paciente", on_delete=models.PROTECT, related_name="home_visits")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="profesional asignado", null=True, blank=True, on_delete=models.PROTECT, related_name="home_visits")
    scheduled_for = models.DateTimeField("fecha y hora")
    visit_type = models.CharField("tipo de visita", max_length=20, choices=VisitType.choices, default=VisitType.CLINICAL)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.REQUESTED)
    address = models.CharField("dirección", max_length=180)
    zone = models.CharField("zona o barrio", max_length=100, blank=True)
    reason = models.CharField("motivo", max_length=180)
    notes = models.TextField("observaciones", blank=True)
    price = models.DecimalField("valor sugerido", max_digits=12, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(Decimal("0"))])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_for", "id"]
        verbose_name = "visita a domicilio"
        verbose_name_plural = "visitas a domicilio"

    def __str__(self):
        return f"{self.patient} · {self.scheduled_for:%d/%m %H:%M}"
