from datetime import datetime, timedelta
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from patients.models import Patient
from .models import GroomingAppointment, GroomingService


class GroomingAppointmentTests(TestCase):
    def setUp(self):
        self.patient = Patient.objects.create(name="Mora", species="dog")
        self.service = GroomingService.objects.create(name="Baño y corte", duration_minutes=60)

    def test_appointment_calculates_end_time(self):
        starts_at = timezone.make_aware(datetime(2026, 7, 30, 10, 0))
        appointment = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=starts_at)
        self.assertEqual(appointment.ends_at, timezone.make_aware(datetime(2026, 7, 30, 11, 0)))

    def test_active_appointments_cannot_overlap(self):
        GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.make_aware(datetime(2026, 7, 30, 10, 0)))
        with self.assertRaises(ValidationError):
            GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.make_aware(datetime(2026, 7, 30, 10, 30)))


class AgendaDailyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("agenda-user", password="secret")
        self.user.user_permissions.add(Permission.objects.get(codename="view_groomingappointment"))
        self.patient = Patient.objects.create(name="Lola", species="dog")
        self.service = GroomingService.objects.create(name="Baño", duration_minutes=30)
        self.client.force_login(self.user)

    def test_agenda_exposes_daily_delays_and_next_appointment(self):
        now = timezone.now()
        delayed = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=now - timedelta(hours=1), status="confirmed")
        upcoming = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Toto", species="dog"), service=self.service, starts_at=now + timedelta(hours=2), status="booked")
        GroomingAppointment.objects.create(patient=Patient.objects.create(name="Mora", species="dog"), service=self.service, starts_at=now - timedelta(hours=3), status="done")
        response = self.client.get(reverse("grooming_agenda"))
        self.assertContains(response, "Demorados")
        self.assertIn(delayed, response.context["delayed_appointments"])
        self.assertEqual(response.context["next_appointment"], upcoming)

    def test_today_scope_limits_visible_cards_to_today(self):
        today_appointment = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1))
        tomorrow_appointment = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Nina", species="cat"), service=self.service, starts_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse("grooming_agenda"), {"view": "day"})
        self.assertContains(response, today_appointment.patient.name)
        self.assertNotContains(response, tomorrow_appointment.patient.name)

    def test_agenda_filters_by_status_and_assigned_professional(self):
        professional = User.objects.create_user("groomer", password="secret", first_name="Carla")
        matching = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1), status="confirmed", assigned_to=professional)
        other = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Nina", species="cat"), service=self.service, starts_at=timezone.now() + timedelta(hours=2), status="booked")
        response = self.client.get(reverse("grooming_agenda"), {"view": "day", "status": "confirmed", "employee": professional.id})
        self.assertContains(response, matching.patient.name)
        self.assertNotContains(response, other.patient.name)
        self.assertContains(response, "Carla")
