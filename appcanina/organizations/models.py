from django.conf import settings
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
    locality = models.CharField("localidad", max_length=120, blank=True)
    donation_alias = models.CharField("alias para colaboraciones", max_length=120, blank=True)
    donation_message = models.CharField(
        "mensaje de colaboración", max_length=220, blank=True,
        help_text="Se verá debajo de las publicaciones de adopción del refugio.",
    )

    class Meta:
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Responsable"
        STAFF = "staff", "Equipo"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="organization_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MANAGER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "user"], name="unique_organization_membership")]
        verbose_name = "integrante de organización"
        verbose_name_plural = "integrantes de organizaciones"

    def __str__(self):
        return f"{self.user} · {self.organization}"
