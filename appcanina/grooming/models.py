from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from patients.models import Patient


class GroomingService(models.Model):
    name = models.CharField("nombre", max_length=100)
    duration_minutes = models.PositiveIntegerField("duración en minutos", default=60)
    price = models.DecimalField("precio sugerido", max_digits=12, decimal_places=2, default=Decimal("0"))
    active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "servicio de peluquería"
        verbose_name_plural = "servicios de peluquería"

    def __str__(self): return self.name


class GroomingAppointment(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Reservado"
        CONFIRMED = "confirmed", "Confirmado"
        DONE = "done", "Finalizado"
        CANCELED = "canceled", "Cancelado"
    patient = models.ForeignKey(Patient, verbose_name="paciente", on_delete=models.PROTECT, related_name="grooming_appointments")
    service = models.ForeignKey(GroomingService, verbose_name="servicio", on_delete=models.PROTECT)
    additional_services = models.ManyToManyField(GroomingService, verbose_name="servicios adicionales", blank=True, related_name="additional_appointments")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="profesional asignado", on_delete=models.PROTECT, related_name="assigned_grooming_appointments", null=True, blank=True)
    starts_at = models.DateTimeField("fecha y hora")
    ends_at = models.DateTimeField("finaliza", editable=False)
    status = models.CharField("estado", max_length=12, choices=Status.choices, default=Status.BOOKED)
    notes = models.TextField("notas", blank=True)

    class Meta:
        ordering = ["starts_at"]
        verbose_name = "turno de peluquería"
        verbose_name_plural = "turnos de peluquería"

    def clean(self):
        total_minutes = self.service.duration_minutes
        if self.pk:
            total_minutes += sum(service.duration_minutes for service in self.additional_services.all())
        self.ends_at = self.starts_at + timedelta(minutes=total_minutes)
        if self.status != self.Status.CANCELED and GroomingAppointment.objects.filter(starts_at__lt=self.ends_at, ends_at__gt=self.starts_at).exclude(pk=self.pk).exclude(status=self.Status.CANCELED).exists():
            raise ValidationError("El horario se superpone con otro turno activo.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def update_end_time_from_services(self):
        self.full_clean()
        super().save(update_fields=["ends_at"])
