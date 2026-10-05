from django.db import models


class Organization(models.Model):
    class Kind(models.TextChoices):
        VETERINARY = "veterinary", "Veterinaria"
        SHELTER = "shelter", "Refugio o perrera"

    name = models.CharField("nombre", max_length=160)
    kind = models.CharField("tipo", max_length=20, choices=Kind.choices)
    is_business_profile = models.BooleanField("es el perfil del negocio", default=False)
    logo = models.ImageField("logo", upload_to="organizations/logos/", blank=True)
    phone = models.CharField("teléfono", max_length=40, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    address = models.CharField("dirección", max_length=220, blank=True)

    class Meta:
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"

    def __str__(self):
        return self.name
