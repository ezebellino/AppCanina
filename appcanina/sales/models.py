from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from inventory.models import Product
from grooming.models import GroomingService
from patients.models import Contact, Patient


class Sale(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "cash", "Efectivo"
        TRANSFER = "transfer", "Transferencia"
        QR = "qr", "QR"

    patient = models.ForeignKey(Patient, verbose_name="paciente", on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    contact = models.ForeignKey(Contact, verbose_name="cliente o responsable", on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    product = models.ForeignKey(Product, verbose_name="producto principal legado", on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    quantity = models.DecimalField("cantidad principal legado", max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))], null=True, blank=True)
    unit_price = models.DecimalField("precio unitario aplicado legado", max_digits=12, decimal_places=2, null=True, blank=True)
    total = models.DecimalField("total", max_digits=12, decimal_places=2)
    payment_method = models.CharField("medio de pago", max_length=12, choices=PaymentMethod.choices)
    payment_reference = models.CharField("referencia de pago", max_length=120, blank=True)
    grooming_appointment = models.OneToOneField("grooming.GroomingAppointment", verbose_name="turno de peluquería", on_delete=models.PROTECT, related_name="sale", null=True, blank=True)
    cash_session = models.ForeignKey("CashSession", verbose_name="sesión de caja", on_delete=models.PROTECT, related_name="sales", null=True, blank=True)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="vendedor", on_delete=models.PROTECT, related_name="sales")
    created_at = models.DateTimeField("fecha y hora", default=timezone.now)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "venta"
        verbose_name_plural = "ventas"

    def __str__(self):
        return f"Venta #{self.pk}"


class SaleLine(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="lines")
    product = models.ForeignKey(Product, verbose_name="producto", on_delete=models.PROTECT, null=True, blank=True)
    service = models.ForeignKey(GroomingService, verbose_name="servicio", on_delete=models.PROTECT, null=True, blank=True)
    description = models.CharField("descripción", max_length=180)
    quantity = models.DecimalField("cantidad", max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal("0.001"))])
    unit_price = models.DecimalField("precio unitario", max_digits=12, decimal_places=2)
    total = models.DecimalField("subtotal", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "línea de venta"
        verbose_name_plural = "líneas de venta"


class CashSession(models.Model):
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="opened_cash_sessions")
    opened_at = models.DateTimeField(auto_now_add=True)
    opening_amount = models.DecimalField("monto inicial", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    closed_at = models.DateTimeField(null=True, blank=True)
    closing_amount = models.DecimalField("efectivo contado", max_digits=12, decimal_places=2, null=True, blank=True)
    closing_notes = models.TextField("observación de cierre", blank=True)

    class Meta:
        ordering = ["-opened_at"]
        verbose_name = "sesión de caja"
        verbose_name_plural = "sesiones de caja"

    @property
    def is_open(self): return self.closed_at is None


class CashMovement(models.Model):
    class Kind(models.TextChoices):
        INCOME = "income", "Ingreso manual"
        WITHDRAWAL = "withdrawal", "Retiro de caja"
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField("tipo", max_length=12, choices=Kind.choices)
    amount = models.DecimalField("importe", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    note = models.CharField("motivo", max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)
