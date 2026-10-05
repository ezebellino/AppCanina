from django.db import models
from django.conf import settings
from django.utils import timezone
from organizations.models import Organization


class Contact(models.Model):
    class Kind(models.TextChoices):
        PERSON = "person", "Persona"
        INSTITUTION = "institution", "Institución"

    full_name = models.CharField("nombre completo o razón social", max_length=160)
    kind = models.CharField("tipo", max_length=16, choices=Kind.choices, default=Kind.PERSON)
    phone = models.CharField("teléfono", max_length=40, blank=True)
    email = models.EmailField("correo electrónico", blank=True)

    def __str__(self):
        return self.full_name


class Patient(models.Model):
    class Species(models.TextChoices):
        DOG = "dog", "Perro"
        CAT = "cat", "Gato"
        OTHER = "other", "Otra"

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, null=True, blank=True, related_name="patients")
    name = models.CharField("nombre", max_length=100)
    species = models.CharField("especie", max_length=12, choices=Species.choices)
    breed = models.CharField("raza", max_length=100, blank=True)
    birth_date = models.DateField("fecha de nacimiento", null=True, blank=True)
    microchip = models.CharField("microchip o identificación", max_length=80, blank=True)
    photo = models.ImageField("foto", upload_to="patients/%Y/%m/", blank=True)
    allergies = models.TextField("alergias", blank=True)
    notes = models.TextField("observaciones", blank=True)
    active = models.BooleanField("activo", default=True)
    contacts = models.ManyToManyField(Contact, through="PatientContact", related_name="patients")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PatientContact(models.Model):
    class Role(models.TextChoices):
        RESPONSIBLE = "responsible", "Responsable"
        ADOPTER = "adopter", "Adoptante"
        CUSTODIAN = "custodian", "Cuidador"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.PROTECT)
    role = models.CharField("vínculo", max_length=16, choices=Role.choices)
    is_primary = models.BooleanField("contacto principal", default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["patient", "contact", "role"], name="unique_patient_contact_role")]


class ClinicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="clinical_records")
    occurred_on = models.DateField("fecha", default=timezone.localdate)
    reason = models.CharField("motivo de consulta", max_length=180)
    notes = models.TextField("observaciones")
    professional = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="clinical_records")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-occurred_on", "-id"]
        verbose_name = "registro clínico"
        verbose_name_plural = "registros clínicos"

    def __str__(self):
        return f"{self.patient} · {self.reason}"


class CareReminder(models.Model):
    class Kind(models.TextChoices):
        VACCINE = "vaccine", "Vacuna"
        ANTIPARASITIC = "antiparasitic", "Antiparasitario"
        CLINICAL_CONTROL = "clinical_control", "Control clínico"
        MEDICATION = "medication", "Medicación"
        OTHER = "other", "Otro"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="care_reminders", verbose_name="paciente")
    kind = models.CharField("tipo", max_length=20, choices=Kind.choices)
    due_on = models.DateField("fecha prevista")
    notes = models.CharField("detalle", max_length=180, blank=True)
    completed_on = models.DateField("realizado el", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_on", "id"]
        verbose_name = "recordatorio de cuidado"
        verbose_name_plural = "recordatorios de cuidado"

    @property
    def is_completed(self):
        return self.completed_on is not None

    def __str__(self):
        return f"{self.patient} · {self.get_kind_display()}"
