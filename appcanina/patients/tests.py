from io import BytesIO
from datetime import timedelta

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from inventory.models import Brand, Product, Supplier
from PIL import Image
from unittest.mock import patch
from django.db import OperationalError
from .models import (
    CareReminder,
    ClinicalHistoryAccessLog,
    ClinicalRecord,
    Contact,
    OwnerAccountLink,
    Patient,
    PatientContact,
    PatientSharingConsent,
    TravelAccessRequest,
    TravelCredential,
)
from organizations.models import Organization, OrganizationMembership
from sales.models import Sale


class RoleAccessTests(TestCase):
    def user_with(self, *codes):
        user = User.objects.create_user("employee", password="secret")
        group, _ = Group.objects.get_or_create(name="test-role")
        group.permissions.set(Permission.objects.filter(content_type__app_label="patients", codename__in=codes))
        user.groups.add(group)
        organization = Organization.objects.create(name=f"Clínica de {user.username}", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=organization, user=user)
        Patient.objects.filter(organization__isnull=True).update(organization=organization)
        return user

    def test_employee_can_read_patients_but_cannot_create(self):
        user = self.user_with("view_patient")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("patient_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("patient_create")).status_code, 403)

    def test_employee_can_view_detail_but_cannot_edit(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("patient_detail", args=[patient.id])).status_code, 200)
        self.assertEqual(self.client.get(reverse("patient_edit", args=[patient.id])).status_code, 403)

    def test_patient_detail_shows_own_and_responsible_sales_when_allowed(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        other_patient = Patient.objects.create(name="Milo", species="cat")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        seller = User.objects.create_user("seller", password="secret")
        Sale.objects.create(patient=patient, contact=contact, total=1000, payment_method="transfer", seller=seller)
        Sale.objects.create(patient=other_patient, contact=contact, total=2000, payment_method="qr", seller=seller)
        user = User.objects.create_user("viewer", password="secret")
        user.user_permissions.add(Permission.objects.get(codename="view_patient"), Permission.objects.get(codename="view_sale"))
        organization = Organization.objects.create(name="Clínica del viewer", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=organization, user=user)
        Patient.objects.filter(pk__in=[patient.id, other_patient.id]).update(organization=organization)
        self.client.force_login(user)
        response = self.client.get(reverse("patient_detail", args=[patient.id]))
        self.assertContains(response, "Compras de Luna")
        self.assertContains(response, "Otras compras de sus responsables")
        self.assertContains(response, "Milo")

    def test_global_search_finds_patient_contact_and_product_by_shared_term(self):
        contact = Contact.objects.create(full_name="Carmela Martinez", phone="11 5555 1234")
        patient = Patient.objects.create(name="Luna", species="cat", microchip="CHIP-123")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        brand = Brand.objects.create(name="Marca Luna")
        supplier = Supplier.objects.create(name="Proveedor Luna")
        Product.objects.create(name="Alimento Luna", category="food", brand=brand, supplier=supplier, price=1000)
        user = User.objects.create_user("searcher", password="secret")
        user.user_permissions.add(Permission.objects.get(content_type__app_label="patients", codename="view_patient"), Permission.objects.get(content_type__app_label="inventory", codename="view_product"))
        organization = Organization.objects.create(name="Clínica del buscador", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=organization, user=user)
        patient.organization = organization
        patient.save(update_fields=["organization"])
        self.client.force_login(user)
        response = self.client.get(reverse("global_search"), {"q": "Luna"})
        self.assertContains(response, patient.name)
        self.assertContains(response, "Alimento Luna")
        response = self.client.get(reverse("global_search"), {"q": "Carmela"})
        self.assertContains(response, contact.full_name)
        self.assertContains(response, patient.name)

    def test_administrator_permissions_allow_patient_creation_page(self):
        user = self.user_with("view_patient", "add_patient", "add_contact", "add_patientcontact")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("patient_create")).status_code, 200)

    def test_patient_creation_reuses_matching_contact(self):
        contact = Contact.objects.create(full_name="Ana Pérez", kind="person", phone="11 1111 1111", email="ana@example.com")
        user = self.user_with("view_patient", "add_patient", "add_contact", "add_patientcontact")
        self.client.force_login(user)
        response = self.client.post(reverse("patient_create"), {"patient-name": "Nina", "patient-species": "dog", "patient-breed": "", "patient-birth_date": "", "patient-microchip": "", "patient-allergies": "", "patient-notes": "", "contact-full_name": "Ana Pérez", "contact-kind": "person", "contact-phone": "11 1111 1111", "contact-email": "ana@example.com"})
        self.assertRedirects(response, reverse("patient_list"))
        self.assertEqual(Contact.objects.filter(full_name="Ana Pérez").count(), 1)
        self.assertEqual(PatientContact.objects.get(patient__name="Nina").contact, contact)

    def test_existing_contact_can_be_linked_to_another_patient(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Nina", species="dog")
        user = self.user_with("view_patient", "add_contact", "add_patientcontact")
        self.client.force_login(user)
        response = self.client.post(reverse("patient_contact_create", args=[patient.id]), {"action": "existing", "existing-contact": contact.id, "existing-role": "responsible", "existing-is_primary": "on"})
        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        self.assertEqual(PatientContact.objects.get(patient=patient).contact, contact)

    def test_command_merges_contacts_with_identical_data(self):
        first = Contact.objects.create(full_name="Ana Pérez", phone="11 1111", email="ana@example.com")
        duplicate = Contact.objects.create(full_name="Ana Pérez", phone="11 1111", email="ana@example.com")
        patient = Patient.objects.create(name="Luna", species="cat")
        PatientContact.objects.create(patient=patient, contact=duplicate, role="responsible", is_primary=True)
        seller = User.objects.create_user("seller-merge", password="secret")
        sale = Sale.objects.create(contact=duplicate, total=1000, payment_method="transfer", seller=seller)
        call_command("merge_duplicate_contacts")
        self.assertEqual(Contact.objects.filter(full_name="Ana Pérez").count(), 1)
        self.assertEqual(PatientContact.objects.get(patient=patient).contact, first)
        sale.refresh_from_db()
        self.assertEqual(sale.contact, first)

    def test_user_with_change_permissions_updates_patient_and_contact(self):
        contact = Contact.objects.create(full_name="Ana Pérez", phone="11 0000 0000")
        patient = Patient.objects.create(name="Luna", species="cat", breed="Común")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient", "change_patient", "change_contact", "change_patientcontact")
        self.client.force_login(user)

        response = self.client.post(reverse("patient_edit", args=[patient.id]), {
            "patient-name": "Luna Actualizada",
            "patient-species": "cat",
            "patient-breed": "Siamesa",
            "patient-birth_date": "",
            "patient-microchip": "ABC-123",
            "patient-allergies": "Ninguna",
            "patient-notes": "Control anual pendiente",
            "contact-full_name": "Ana Pérez",
            "contact-kind": "person",
            "contact-phone": "11 2222 2222",
            "contact-email": "ana@example.com",
        })

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        patient.refresh_from_db()
        contact.refresh_from_db()
        self.assertEqual(patient.name, "Luna Actualizada")
        self.assertEqual(patient.microchip, "ABC-123")
        self.assertEqual(contact.phone, "11 2222 2222")

    def test_patient_edit_shows_a_safe_message_when_database_is_temporarily_unavailable(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient", "change_patient", "change_contact", "change_patientcontact")
        self.client.force_login(user)
        payload = {
            "patient-name": "Luna",
            "patient-species": "cat",
            "patient-breed": "",
            "patient-birth_date": "",
            "patient-microchip": "",
            "patient-allergies": "",
            "patient-notes": "",
            "contact-full_name": "Ana Pérez",
            "contact-kind": "person",
            "contact-phone": "",
            "contact-email": "",
        }

        with patch("patients.views.PatientForm.save", side_effect=OperationalError("database is locked")):
            response = self.client.post(reverse("patient_edit", args=[patient.id]), payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No se pudieron guardar los cambios")
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Luna")

    def test_user_can_rename_a_patient_and_upload_a_photo_in_the_same_edit(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient", "change_patient", "change_contact", "change_patientcontact")
        self.client.force_login(user)
        image_bytes = BytesIO()
        Image.new("RGB", (2, 2), color="#087d78").save(image_bytes, format="PNG")
        photo = SimpleUploadedFile("luna.png", image_bytes.getvalue(), content_type="image/png")

        response = self.client.post(
            reverse("patient_edit", args=[patient.id]),
            {
                "patient-name": "Luna Renombrada",
                "patient-species": "cat",
                "patient-breed": "",
                "patient-birth_date": "",
                "patient-microchip": "",
                "patient-photo": photo,
                "patient-allergies": "",
                "patient-notes": "",
                "contact-full_name": "Ana Pérez",
                "contact-kind": "person",
                "contact-phone": "",
                "contact-email": "",
            },
        )

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        patient.refresh_from_db()
        self.assertEqual(patient.name, "Luna Renombrada")
        self.assertTrue(patient.photo.name)
        image_response = self.client.get(patient.photo.url)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.headers["Content-Type"], "image/png")


class OrganizationClinicalIsolationTests(TestCase):
    """Regression tests for the clinical tenant boundary."""

    def setUp(self):
        self.organization_a = Organization.objects.create(name="Veterinaria A", kind=Organization.Kind.VETERINARY)
        self.organization_b = Organization.objects.create(name="Veterinaria B", kind=Organization.Kind.VETERINARY)
        self.user_a = User.objects.create_user("professional-a", password="secret")
        self.user_a.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="patients",
            codename__in=["view_patient", "change_patient", "change_contact", "change_patientcontact", "add_clinicalrecord", "add_carereminder", "change_carereminder", "view_carereminder", "delete_patient"],
        ))
        OrganizationMembership.objects.create(organization=self.organization_a, user=self.user_a)
        self.patient_a = Patient.objects.create(name="Luna A", species="cat", organization=self.organization_a)
        self.patient_b = Patient.objects.create(name="Luna B", species="dog", organization=self.organization_b)
        self.reminder_b = CareReminder.objects.create(patient=self.patient_b, kind=CareReminder.Kind.VACCINE, due_on="2026-11-01")
        self.client.force_login(self.user_a)

    def test_list_and_search_only_show_the_member_organization(self):
        response = self.client.get(reverse("patient_list"))
        self.assertContains(response, self.patient_a.name)
        self.assertNotContains(response, self.patient_b.name)

        response = self.client.get(reverse("global_search"), {"q": "Luna"})
        self.assertContains(response, self.patient_a.name)
        self.assertNotContains(response, self.patient_b.name)

    def test_other_organization_patient_cannot_be_read_or_mutated_by_id(self):
        self.assertEqual(self.client.get(reverse("patient_detail", args=[self.patient_b.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("patient_edit", args=[self.patient_b.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("clinical_record_create", args=[self.patient_b.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("care_reminder_create", args=[self.patient_b.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("care_reminder_complete", args=[self.reminder_b.id])).status_code, 404)
        self.assertEqual(self.client.post(reverse("patient_archive", args=[self.patient_b.id])).status_code, 404)
        self.patient_b.refresh_from_db()
        self.reminder_b.refresh_from_db()
        self.assertTrue(self.patient_b.active)
        self.assertIsNone(self.reminder_b.completed_on)

    def test_patient_creation_assigns_the_organization_on_the_server(self):
        self.user_a.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="patients", codename__in=["add_patient", "add_contact", "add_patientcontact"],
        ))
        response = self.client.post(reverse("patient_create"), {
            "patient-name": "Mora", "patient-species": "cat", "patient-breed": "", "patient-birth_date": "",
            "patient-microchip": "", "patient-allergies": "", "patient-notes": "",
            "contact-full_name": "Ana", "contact-kind": "person", "contact-phone": "", "contact-email": "",
            "patient-organization": self.organization_b.id,
        })
        self.assertRedirects(response, reverse("patient_list"))
        self.assertEqual(Patient.objects.get(name="Mora").organization, self.organization_a)


class CareReminderTests(TestCase):
    def user_with(self, *codes):
        user = User.objects.create_user("employee", password="secret")
        group, _ = Group.objects.get_or_create(name="test-role")
        group.permissions.set(Permission.objects.filter(content_type__app_label="patients", codename__in=codes))
        user.groups.add(group)
        organization = Organization.objects.create(name=f"Clínica de {user.username}", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=organization, user=user)
        Patient.objects.filter(organization__isnull=True).update(organization=organization)
        return user

    def setUp(self):
        self.user = User.objects.create_user("reminder-user", password="secret")
        self.user.user_permissions.add(
            Permission.objects.get(codename="view_patient"),
            Permission.objects.get(codename="add_carereminder"),
            Permission.objects.get(codename="view_carereminder"),
            Permission.objects.get(codename="change_carereminder"),
        )
        self.organization = Organization.objects.create(name="Clínica de recordatorios", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.patient = Patient.objects.create(name="Mora", species="dog", organization=self.organization)
        self.client.force_login(self.user)

    def test_reminder_can_be_created_and_completed_from_patient_flow(self):
        response = self.client.post(reverse("care_reminder_create", args=[self.patient.id]), {"kind": "vaccine", "due_on": "2026-10-01", "notes": "Refuerzo anual"})
        self.assertRedirects(response, reverse("patient_detail", args=[self.patient.id]))
        reminder = CareReminder.objects.get()
        response = self.client.post(reverse("care_reminder_complete", args=[reminder.id]), {"next": reverse("patient_detail", args=[self.patient.id])})
        self.assertRedirects(response, reverse("patient_detail", args=[self.patient.id]))
        reminder.refresh_from_db()
        self.assertIsNotNone(reminder.completed_on)

    def test_daily_animal_care_only_shows_visible_due_reminders(self):
        today = timezone.localdate()
        due = CareReminder.objects.create(patient=self.patient, kind="vaccine", due_on=today, notes="Refuerzo")
        foreign_org = Organization.objects.create(name="Otra clínica", kind=Organization.Kind.VETERINARY)
        foreign_patient = Patient.objects.create(name="Oculto", species="cat", organization=foreign_org)
        CareReminder.objects.create(patient=foreign_patient, kind="medication", due_on=today)

        response = self.client.get(reverse("daily_animal_care"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, due.patient.name)
        self.assertNotContains(response, foreign_patient.name)

    def test_user_with_add_permissions_can_add_adopter_and_change_primary_contact(self):
        original_contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        original_relation = PatientContact.objects.create(patient=patient, contact=original_contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient", "add_contact", "add_patientcontact")
        self.client.force_login(user)

        response = self.client.post(reverse("patient_contact_create", args=[patient.id]), {
            "contact-full_name": "Refugio Patitas",
            "contact-kind": "institution",
            "contact-phone": "11 3333 3333",
            "contact-email": "contacto@patitas.example",
            "relation-role": "adopter",
            "relation-is_primary": "on",
        })

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        original_relation.refresh_from_db()
        new_relation = PatientContact.objects.get(patient=patient, contact__full_name="Refugio Patitas")
        self.assertFalse(original_relation.is_primary)
        self.assertTrue(new_relation.is_primary)
        self.assertEqual(new_relation.role, "adopter")

    def test_employee_cannot_add_patient_contact(self):
        patient = Patient.objects.create(name="Luna", species="cat")
        user = self.user_with("view_patient")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("patient_contact_create", args=[patient.id])).status_code, 403)

    def test_user_with_change_permission_can_edit_role_and_primary_contact(self):
        first_contact = Contact.objects.create(full_name="Ana Pérez")
        second_contact = Contact.objects.create(full_name="Bruno López")
        patient = Patient.objects.create(name="Luna", species="cat")
        first_relation = PatientContact.objects.create(patient=patient, contact=first_contact, role="responsible", is_primary=True)
        second_relation = PatientContact.objects.create(patient=patient, contact=second_contact, role="custodian", is_primary=False)
        user = self.user_with("view_patient", "change_patientcontact")
        self.client.force_login(user)

        response = self.client.post(reverse("patient_contact_edit", args=[patient.id, second_relation.id]), {
            "role": "adopter",
            "is_primary": "on",
        })

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        first_relation.refresh_from_db()
        second_relation.refresh_from_db()
        self.assertFalse(first_relation.is_primary)
        self.assertTrue(second_relation.is_primary)
        self.assertEqual(second_relation.role, "adopter")

    def test_removing_primary_relation_preserves_contact_and_promotes_remaining_relation(self):
        first_contact = Contact.objects.create(full_name="Ana Pérez")
        second_contact = Contact.objects.create(full_name="Bruno López")
        patient = Patient.objects.create(name="Luna", species="cat")
        first_relation = PatientContact.objects.create(patient=patient, contact=first_contact, role="responsible", is_primary=True)
        second_relation = PatientContact.objects.create(patient=patient, contact=second_contact, role="custodian", is_primary=False)
        user = self.user_with("view_patient", "delete_patientcontact")
        self.client.force_login(user)

        response = self.client.post(reverse("patient_contact_remove", args=[patient.id, first_relation.id]))

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        self.assertFalse(PatientContact.objects.filter(pk=first_relation.id).exists())
        self.assertTrue(Contact.objects.filter(pk=first_contact.id).exists())
        second_relation.refresh_from_db()
        self.assertTrue(second_relation.is_primary)

    def test_employee_cannot_remove_patient_contact(self):
        contact = Contact.objects.create(full_name="Ana Pérez")
        patient = Patient.objects.create(name="Luna", species="cat")
        relation = PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        user = self.user_with("view_patient")
        self.client.force_login(user)
        self.assertEqual(self.client.post(reverse("patient_contact_remove", args=[patient.id, relation.id])).status_code, 403)

    def test_user_with_clinical_permission_can_add_record_with_professional(self):
        patient = Patient.objects.create(name="Luna", species="cat")
        user = self.user_with("view_patient", "view_clinicalrecord", "add_clinicalrecord")
        self.client.force_login(user)

        response = self.client.post(reverse("clinical_record_create", args=[patient.id]), {
            "occurred_on": "2026-07-29",
            "reason": "Control preventivo",
            "notes": "Paciente en buen estado general.",
        })

        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        record = ClinicalRecord.objects.get(patient=patient)
        self.assertEqual(record.professional, user)
        self.assertEqual(record.reason, "Control preventivo")

    def test_employee_without_clinical_permission_cannot_add_record(self):
        patient = Patient.objects.create(name="Luna", species="cat")
        user = self.user_with("view_patient")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("clinical_record_create", args=[patient.id])).status_code, 403)


class TravelClinicalAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("responsable", password="secret")
        self.contact = Contact.objects.create(full_name="Ana Pérez")
        self.patient = Patient.objects.create(name="Luna", species="cat", microchip="CHIP-123")
        PatientContact.objects.create(
            patient=self.patient,
            contact=self.contact,
            role=PatientContact.Role.RESPONSIBLE,
            is_primary=True,
        )
        OwnerAccountLink.objects.create(contact=self.contact, user=self.owner)
        self.organization = Organization.objects.create(
            name="Veterinaria Capital",
            kind=Organization.Kind.VETERINARY,
            locality="Capital Federal",
        )
        self.professional = User.objects.create_user("veterinaria", password="secret")
        self.professional.user_permissions.add(Permission.objects.get(codename="view_clinicalrecord"))
        OrganizationMembership.objects.create(organization=self.organization, user=self.professional)
        ClinicalRecord.objects.create(
            patient=self.patient,
            professional=self.professional,
            reason="Control preventivo",
            notes="Paciente en buen estado.",
        )

    def test_owner_can_issue_a_portable_credential_only_for_linked_patient(self):
        self.client.force_login(self.owner)

        response = self.client.get(reverse("my_animal_credential", args=[self.patient.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(TravelCredential.objects.filter(patient=self.patient, contact=self.contact).count(), 1)

    def test_verified_veterinary_gets_audited_temporary_access_after_consent(self):
        PatientSharingConsent.objects.create(patient=self.patient, contact=self.contact, enabled=True)
        code, credential = TravelCredential.issue(self.patient, self.contact, expires_at=timezone.now() + timedelta(days=1))
        self.client.force_login(self.professional)

        response = self.client.post(
            reverse("travel_access_request"),
            {"credential_code": code, "locality": "capital federal", "purpose": "Control durante viaje"},
        )

        access = TravelAccessRequest.objects.get(credential=credential)
        self.assertTrue(access.is_active)
        self.assertRedirects(response, reverse("travel_access_history", args=[access.id]))

        response = self.client.get(reverse("travel_access_history", args=[access.id]))

        self.assertContains(response, "Control preventivo")
        self.assertEqual(ClinicalHistoryAccessLog.objects.filter(travel_request=access).count(), 1)

    def test_access_is_denied_without_explicit_sharing_consent(self):
        code, credential = TravelCredential.issue(self.patient, self.contact, expires_at=timezone.now() + timedelta(days=1))
        self.client.force_login(self.professional)

        response = self.client.post(
            reverse("travel_access_request"),
            {"credential_code": code, "locality": "Capital Federal", "purpose": "Control durante viaje"},
        )

        access = TravelAccessRequest.objects.get(credential=credential)
        self.assertFalse(access.is_active)
        self.assertContains(response, "Acceso no autorizado")
