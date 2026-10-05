from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Supplier(models.Model):
    class VisitFrequency(models.TextChoices):
        DAILY = "daily", "Todos los días"
        WEEKLY = "weekly", "Una vez por semana"
        TWICE_WEEKLY = "twice_weekly", "Dos veces por semana"
        AS_NEEDED = "as_needed", "A demanda"
    name = models.CharField("nombre", max_length=140, unique=True)
    phone = models.CharField("teléfono", max_length=40, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    notes = models.TextField("observaciones", blank=True)
    visit_frequency = models.CharField("frecuencia de visita", max_length=16, choices=VisitFrequency.choices, default=VisitFrequency.AS_NEEDED)
    last_visit_on = models.DateField("última visita", null=True, blank=True)
    active = models.BooleanField("activo", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField("nombre", max_length=100, unique=True)
    active = models.BooleanField("activa", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "marca"
        verbose_name_plural = "marcas"

    def __str__(self):
        return self.name


class Product(models.Model):
    class Category(models.TextChoices):
        FOOD = "food", "Alimento"
        TOY = "toy", "Juguete"
        CLOTHING = "clothing", "Abrigo y ropa"
        BED = "bed", "Cama y descanso"
        ACCESSORY = "accessory", "Accesorio"
        HYGIENE = "hygiene", "Higiene"
        SHAMPOO = "shampoo", "Shampoo y cosmética"
        MEDICINE = "medicine", "Medicamento veterinario"
        ANTIPARASITIC = "antiparasitic", "Pipeta y antiparasitario"
        OTHER = "other", "Otro"

    class SaleUnit(models.TextChoices):
        UNIT = "unit", "Unidad"
        KILOGRAM = "kg", "Kilogramo"
        BAG = "bag", "Bolsa"

    sku = models.CharField("código interno", max_length=50, blank=True, unique=True, null=True)
    name = models.CharField("nombre", max_length=180)
    commercial_name = models.CharField("nombre comercial o profesional", max_length=220, blank=True)
    category = models.CharField("categoría", max_length=16, choices=Category.choices)
    quality = models.CharField("calidad o línea", max_length=80, blank=True)
    brand = models.ForeignKey(Brand, verbose_name="marca", on_delete=models.PROTECT, related_name="products")
    supplier = models.ForeignKey(Supplier, verbose_name="proveedor", on_delete=models.PROTECT, related_name="products")
    sale_unit = models.CharField("se vende por", max_length=8, choices=SaleUnit.choices, default=SaleUnit.UNIT)
    package_weight_kg = models.DecimalField("peso de bolsa (kg)", max_digits=7, decimal_places=3, null=True, blank=True, validators=[MinValueValidator(Decimal("0.001"))])
    price = models.DecimalField("precio habitual", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    promotional_price = models.DecimalField("precio promocional", max_digits=12, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0"))])
    promotion_starts_on = models.DateField("promoción desde", null=True, blank=True)
    promotion_ends_on = models.DateField("promoción hasta", null=True, blank=True)
    stock = models.DecimalField("stock actual", max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(Decimal("0"))])
    minimum_stock = models.DecimalField("stock mínimo", max_digits=10, decimal_places=3, default=0, validators=[MinValueValidator(Decimal("0"))])
    batch = models.CharField("lote", max_length=80, blank=True)
    expires_on = models.DateField("vencimiento", null=True, blank=True)
    requires_prescription = models.BooleanField("requiere receta", default=False)
    active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "producto"
        verbose_name_plural = "productos"

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.commercial_name or self.name

    @property
    def has_active_promotion(self):
        today = timezone.localdate()
        return bool(self.promotional_price is not None and (not self.promotion_starts_on or self.promotion_starts_on <= today) and (not self.promotion_ends_on or today <= self.promotion_ends_on))

    @property
    def current_price(self):
        return self.promotional_price if self.has_active_promotion else self.price

    @property
    def low_stock(self):
        return self.stock <= self.minimum_stock
