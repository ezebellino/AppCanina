from datetime import datetime, timedelta
from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from patients.models import Patient
from organizations.models import Organization, OrganizationMembership
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
        self.organization = Organization.objects.create(name="Clinic", kind="veterinary")
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.patient = Patient.objects.create(name="Lola", species="dog", organization=self.organization)
        self.service = GroomingService.objects.create(name="Baño", duration_minutes=30)
        self.client.force_login(self.user)

    def test_agenda_exposes_daily_delays_and_next_appointment(self):
        now = timezone.now()
        delayed = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=now - timedelta(hours=1), status="confirmed")
        upcoming = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Toto", species="dog", organization=self.organization), service=self.service, starts_at=now + timedelta(hours=2), status="booked")
        GroomingAppointment.objects.create(patient=Patient.objects.create(name="Mora", species="dog", organization=self.organization), service=self.service, starts_at=now - timedelta(hours=3), status="done")
        response = self.client.get(reverse("grooming_agenda"))
        self.assertContains(response, "Demorados")
        self.assertIn(delayed, response.context["delayed_appointments"])
        self.assertEqual(response.context["next_appointment"], upcoming)

    def test_today_scope_limits_visible_cards_to_today(self):
        today_appointment = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1))
        tomorrow_appointment = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Nina", species="cat", organization=self.organization), service=self.service, starts_at=timezone.now() + timedelta(days=1))
        response = self.client.get(reverse("grooming_agenda"), {"view": "day"})
        self.assertContains(response, today_appointment.patient.name)
        self.assertNotContains(response, tomorrow_appointment.patient.name)

    def test_agenda_filters_by_status_and_assigned_professional(self):
        professional = User.objects.create_user("groomer", password="secret", first_name="Carla")
        OrganizationMembership.objects.create(organization=self.organization, user=professional)
        matching = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1), status="confirmed", assigned_to=professional)
        other = GroomingAppointment.objects.create(patient=Patient.objects.create(name="Nina", species="cat", organization=self.organization), service=self.service, starts_at=timezone.now() + timedelta(hours=2), status="booked")
        response = self.client.get(reverse("grooming_agenda"), {"view": "day", "status": "confirmed", "employee": professional.id})
        self.assertContains(response, matching.patient.name)
        self.assertNotContains(response, other.patient.name)
        self.assertContains(response, "Carla")

    def test_motion_only_for_actual_positive_status_change(self):
        self.user.user_permissions.add(Permission.objects.get(codename="change_groomingappointment"))
        item = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1))
        for status, kind in [("confirmed", "booking"), ("done", "grooming")]:
            url = reverse("grooming_appointment_status", args=[item.pk, status])
            response = self.client.post(url, follow=True)
            self.assertContains(response, f'data-success-motion="{kind}"')
            self.assertNotContains(self.client.post(url, follow=True), 'data-success-motion=')
        response = self.client.post(reverse("grooming_appointment_status", args=[item.pk, "canceled"]), follow=True)
        self.assertNotContains(response, 'data-success-motion=')

    def test_unauthorized_status_change_has_no_success_motion(self):
        item = GroomingAppointment.objects.create(patient=self.patient, service=self.service, starts_at=timezone.now() + timedelta(hours=1))
        response = self.client.post(reverse("grooming_appointment_status", args=[item.pk, "done"]))
        self.assertEqual(response.status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.status, "booked")
