import hashlib
import math
import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from patients.models import Patient


def approximate_coordinates(latitude, longitude, marker):
    """Return a stable point roughly 200-280m away from the exact location."""
    if latitude is None or longitude is None:
        return None
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:lost-pets:{marker}".encode()).digest()
    angle = int.from_bytes(digest[:2], "big") / 65535 * math.tau
    distance = 0.0018 + digest[2] / 255 * 0.0007
    latitude_value = float(latitude)
    longitude_value = float(longitude)
    public_latitude = latitude_value + math.cos(angle) * distance
    longitude_scale = max(math.cos(math.radians(latitude_value)), 0.2)
    public_longitude = longitude_value + math.sin(angle) * distance / longitude_scale
    return round(public_latitude, 6), round(public_longitude, 6)


class LostPetReport(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Publicado"
        HIDDEN = "hidden", "Oculto"
        REJECTED = "rejected", "Rechazado"
        RESOLVED = "resolved", "Resuelto"
        ARCHIVED = "archived", "Archivado"

    patient = models.ForeignKey(Patient, verbose_name="paciente vinculado", null=True, blank=True, on_delete=models.SET_NULL, related_name="lost_pet_reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="creado por", on_delete=models.PROTECT, related_name="lost_pet_reports")
    name = models.CharField("nombre del animal", max_length=100)
    species = models.CharField("especie", max_length=12, choices=Patient.Species.choices)
    breed = models.CharField("raza", max_length=100, blank=True)
    description = models.TextField("señas particulares", blank=True)
    photo = models.ImageField("foto", upload_to="lost-pets/%Y/%m/", blank=True)
    last_seen_at = models.DateTimeField("última vez visto")
    area_label = models.CharField("zona o barrio", max_length=120)
    latitude = models.DecimalField("latitud exacta", max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))])
    longitude = models.DecimalField("longitud exacta", max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))])
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.PUBLISHED)
    requested_via_mobile = models.BooleanField("solicitud enviada desde la comunidad", default=False)
    review_note = models.CharField("nota para la solicitud", max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-last_seen_at", "-id"]
        verbose_name = "aviso de animal extraviado"
        verbose_name_plural = "avisos de animales extraviados"

    def __str__(self):
        return f"{self.name} · {self.get_status_display()}"

    @property
    def public_coordinates(self):
        return approximate_coordinates(self.latitude, self.longitude, f"report:{self.pk}")


class Sighting(models.Model):
    class Status(models.TextChoices):
        PUBLISHED = "published", "Publicado"
        HIDDEN = "hidden", "Oculto"

    report = models.ForeignKey(LostPetReport, verbose_name="aviso", on_delete=models.CASCADE, related_name="sightings")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="reportado por", on_delete=models.PROTECT, related_name="lost_pet_sightings")
    seen_at = models.DateTimeField("fecha y hora del avistamiento", default=timezone.now)
    area_label = models.CharField("zona o barrio", max_length=120)
    description = models.TextField("detalle del avistamiento", blank=True)
    photo = models.ImageField("foto", upload_to="lost-pets/sightings/%Y/%m/", blank=True)
    latitude = models.DecimalField("latitud exacta", max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(Decimal("-90")), MaxValueValidator(Decimal("90"))])
    longitude = models.DecimalField("longitud exacta", max_digits=9, decimal_places=6, null=True, blank=True, validators=[MinValueValidator(Decimal("-180")), MaxValueValidator(Decimal("180"))])
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-seen_at", "-id"]
        verbose_name = "avistamiento"
        verbose_name_plural = "avistamientos"

    def __str__(self):
        return f"{self.report.name} · {self.seen_at:%d/%m %H:%M}"

    @property
    def public_coordinates(self):
        return approximate_coordinates(self.latitude, self.longitude, f"sighting:{self.pk}")


class AdoptionPost(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "En revisión"
        PUBLISHED = "published", "Publicado"
        REJECTED = "rejected", "Rechazado"
        ADOPTED = "adopted", "Adoptado"
        ARCHIVED = "archived", "Archivado"

    publisher = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="publicado por", on_delete=models.PROTECT, related_name="adoption_posts")
    name = models.CharField("nombre del animal", max_length=100)
    species = models.CharField("especie", max_length=12, choices=Patient.Species.choices)
    breed = models.CharField("raza", max_length=100, blank=True)
    age_label = models.CharField("edad aproximada", max_length=80, blank=True)
    description = models.TextField("descripción", blank=True)
    photo = models.ImageField("foto", upload_to="adoptions/%Y/%m/", blank=True)
    area_label = models.CharField("zona o barrio", max_length=120)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.PENDING)
    review_note = models.CharField("nota para quien publicó", max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "-created_at", "-id"]
        verbose_name = "publicación de adopción"
        verbose_name_plural = "publicaciones de adopción"

    def __str__(self):
        return f"{self.name} · {self.get_status_display()}"


class AdoptionInterest(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Recibido"
        CONTACT = "contact", "En conversación"
        INTERVIEW = "interview", "En evaluación"
        COMPLETED = "completed", "Adopción concretada"
        CLOSED = "closed", "No continuó"

    post = models.ForeignKey(AdoptionPost, verbose_name="publicación", on_delete=models.CASCADE, related_name="interests")
    applicant = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="persona interesada", on_delete=models.PROTECT, related_name="adoption_interests")
    message = models.TextField("mensaje", max_length=700)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.RECEIVED)
    staff_note = models.CharField("nota visible para la persona", max_length=280, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["post", "applicant"], name="unique_adoption_interest_per_person")]
        verbose_name = "interés de adopción"
        verbose_name_plural = "intereses de adopción"


class MobileAccessToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mobile_access_tokens")
    label = models.CharField(max_length=80, default="Dispositivo móvil")
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def issue(cls, user, label):
        raw_token = secrets.token_urlsafe(32)
        token = cls.objects.create(user=user, label=(label or "Dispositivo móvil")[:80], digest=hashlib.sha256(raw_token.encode()).hexdigest())
        return raw_token, token

    @classmethod
    def from_raw_token(cls, raw_token):
        return cls.objects.select_related("user").filter(digest=hashlib.sha256(raw_token.encode()).hexdigest(), revoked_at__isnull=True).first()


class MobilePushDevice(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mobile_push_devices")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=12, choices=Platform.choices)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "dispositivo con notificaciones"
        verbose_name_plural = "dispositivos con notificaciones"


class CommunityNotification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="community_notifications")
    report = models.ForeignKey(LostPetReport, on_delete=models.CASCADE, related_name="notifications")
    sighting = models.ForeignKey(Sighting, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=280)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
