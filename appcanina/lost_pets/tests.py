from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from patients.models import ClinicalRecord, Contact, OwnerAccountLink, Patient, PatientContact, PatientFamilyAccess, PatientSharingConsent

from .models import AdoptionInterest, AdoptionPost, CommunityDevicePermission, CommunityNotification, LostPetReport, MobileAccessToken, MobilePushDevice, Sighting
from organizations.roles import ensure_base_roles
from organizations.models import Organization, OrganizationMembership


class LostPetReportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("community-user", password="secret")
        permissions = Permission.objects.filter(codename__in=["view_lostpetreport", "add_lostpetreport", "add_sighting", "change_lostpetreport"])
        self.user.user_permissions.add(*permissions)
        self.organization = Organization.objects.create(name="Veterinaria comunitaria", kind=Organization.Kind.VETERINARY)
        OrganizationMembership.objects.create(organization=self.organization, user=self.user)
        self.patient = Patient.objects.create(name="Toto", species="dog", breed="Mestizo", organization=self.organization)
        self.client.force_login(self.user)

    def sample_photo(self):
        image = Image.new("RGB", (24, 24), "navy")
        content = BytesIO()
        image.save(content, format="JPEG")
        return SimpleUploadedFile("nube.jpg", content.getvalue(), content_type="image/jpeg")

    def test_report_is_published_immediately_and_can_link_a_patient(self):
        response = self.client.post(reverse("lost_pet_create"), {"patient": self.patient.id, "name": "Toto", "species": "dog", "breed": "Mestizo", "description": "Collar azul", "last_seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Barrio Norte", "latitude": "", "longitude": ""})
        report = LostPetReport.objects.get()
        self.assertRedirects(response, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(report.status, LostPetReport.Status.PUBLISHED)
        self.assertEqual(report.patient, self.patient)
        self.assertEqual(report.reporter, self.user)

    def test_sighting_is_published_immediately(self):
        report = LostPetReport.objects.create(reporter=self.user, name="Luna", species="cat", last_seen_at=timezone.now(), area_label="Centro")
        response = self.client.post(reverse("sighting_create", args=[report.id]), {"seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Plaza principal", "description": "Cerca de la fuente", "latitude": "", "longitude": ""})
        sighting = Sighting.objects.get()
        self.assertRedirects(response, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(sighting.status, Sighting.Status.PUBLISHED)
        self.assertEqual(sighting.reporter, self.user)

    def test_map_api_returns_only_approximate_coordinates(self):
        LostPetReport.objects.create(reporter=self.user, name="Nube", species="cat", last_seen_at=timezone.now(), area_label="Centro", latitude=Decimal("-34.603700"), longitude=Decimal("-58.381600"))

        response = self.client.get(reverse("lost_pet_map_data"))

        self.assertEqual(response.status_code, 200)
        marker = response.json()["markers"][0]
        self.assertNotIn("latitude", marker)
        self.assertNotIn("longitude", marker)
        self.assertNotEqual(marker["public_latitude"], -34.6037)
        self.assertNotEqual(marker["public_longitude"], -58.3816)

    def test_community_collaborator_can_only_assist_on_published_reports(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("luz-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        published = LostPetReport.objects.create(reporter=self.user, name="Nube", species="cat", last_seen_at=timezone.now(), area_label="Centro")
        hidden = LostPetReport.objects.create(reporter=self.user, name="Tango", species="dog", last_seen_at=timezone.now(), area_label="Barrio Sur", status=LostPetReport.Status.HIDDEN)

        self.client.force_login(collaborator)

        response = self.client.get(reverse("lost_pet_list", query={"view": "all"}))
        self.assertContains(response, "Nube")
        self.assertNotContains(response, "Tango")
        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[hidden.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("lost_pet_create")).status_code, 403)
        self.assertEqual(self.client.get(reverse("patient_list")).status_code, 403)

        response = self.client.post(
            reverse("sighting_create", args=[published.id]),
            {"seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "area_label": "Plaza", "description": "Lo vi cerca de la fuente", "latitude": "", "longitude": ""},
        )
        self.assertRedirects(response, reverse("lost_pet_detail", args=[published.id]))
        self.assertEqual(Sighting.objects.latest("id").reporter, collaborator)

    def test_administrator_who_also_collaborates_can_open_resolved_report(self):
        roles = ensure_base_roles()
        administrator = User.objects.create_user("admin-colabora", password="secret")
        administrator.groups.add(roles["admin"], roles["collaborator"])
        resolved = LostPetReport.objects.create(
            reporter=self.user,
            name="Hilario",
            species="cat",
            last_seen_at=timezone.now(),
            area_label="Avellaneda",
            status=LostPetReport.Status.RESOLVED,
        )

        self.client.force_login(administrator)

        self.assertEqual(self.client.get(reverse("lost_pet_detail", args=[resolved.id])).status_code, 200)

    def test_community_user_receives_report_notification_with_animal_details(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("luz-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        self.client.force_login(self.user)

        self.client.post(
            reverse("lost_pet_create"),
            {
                "patient": "",
                "name": "Mora",
                "species": "dog",
                "breed": "Mestiza",
                "description": "Tiene collar violeta y una mancha blanca en el pecho.",
                "last_seen_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "area_label": "Barrio Norte",
                "latitude": "",
                "longitude": "",
            },
        )
        notification = CommunityNotification.objects.get(recipient=collaborator)
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")

        response = self.client.get(
            reverse("mobile_notifications"),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(notification.title, "Alerta: Mora está extraviado")
        self.assertEqual(response.status_code, 200)
        item = response.json()["notifications"][0]
        self.assertEqual(item["animal_name"], "Mora")
        self.assertEqual(item["description"], "Tiene collar violeta y una mancha blanca en el pecho.")
        self.assertEqual(item["area"], "Barrio Norte")
        self.assertIsNone(item["photo_url"])

    def test_mobile_user_can_register_a_push_device(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("push-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Android de prueba")

        response = self.client.post(
            reverse("mobile_push_device_register"),
            data='{"push_token":"ExponentPushToken[abc123]","platform":"android"}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["registered"])
        self.assertTrue(MobilePushDevice.objects.filter(user=collaborator, platform="android").exists())

    def test_mobile_permissions_are_private_per_account_and_device(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("permisos-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Android de prueba")

        response = self.client.post(
            reverse("mobile_device_permissions"),
            data='{"device_key":"telefono-prueba","device_name":"Mi Android","platform":"android","camera":"granted","location":"denied","notifications":"unknown"}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["device"]["camera"], "granted")
        self.assertEqual(response.json()["device"]["location"], "denied")
        self.assertTrue(CommunityDevicePermission.objects.filter(user=collaborator, device_key="telefono-prueba").exists())

    def test_mobile_collaborator_can_publish_sighting_with_photo_and_private_coordinates(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("veo-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")
        report = LostPetReport.objects.create(reporter=self.user, name="Mora", species="dog", last_seen_at=timezone.now(), area_label="Centro")

        response = self.client.post(
            reverse("mobile_sighting_create", args=[report.id]),
            data={"area": "Plaza central", "description": "Iba hacia la avenida.", "latitude": "-34.603700", "longitude": "-58.381600", "photo": self.sample_photo()},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        sighting = Sighting.objects.get(report=report)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(sighting.reporter, collaborator)
        self.assertEqual(sighting.latitude, Decimal("-34.603700"))
        self.assertTrue(bool(sighting.photo))
        self.assertTrue(CommunityNotification.objects.filter(recipient=self.user, sighting=sighting).exists())

    def test_mobile_registration_creates_only_a_community_collaborator(self):
        response = self.client.post(
            reverse("mobile_register"),
            data='{"username":"sofia-colabora","first_name":"Sofía","password":"ClaveSegura123","password_confirmation":"ClaveSegura123","device_name":"Android de Sofía"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        collaborator = User.objects.get(username="sofia-colabora")
        self.assertTrue(collaborator.groups.filter(name="Colaborador comunitario").exists())
        self.assertTrue(collaborator.has_perm("lost_pets.view_lostpetreport"))
        self.assertTrue(collaborator.has_perm("lost_pets.add_sighting"))
        self.assertFalse(collaborator.has_perm("patients.view_patient"))
        self.assertIn("token", response.json())

    def test_mobile_registration_creates_pending_veterinary_profile_without_staff_permissions(self):
        response = self.client.post(
            reverse("mobile_register"),
            data='{"username":"veterinaria-nueva","first_name":"Laura","email":"laura@example.com","password":"ClaveSegura123","password_confirmation":"ClaveSegura123","account_type":"veterinary","organization_name":"Veterinaria del Parque","locality":"Avellaneda","organization_phone":"11 5555 1234","donation_alias":"veterinaria.parque"}',
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        organization = Organization.objects.get(name="Veterinaria del Parque")
        user = User.objects.get(username="veterinaria-nueva")
        self.assertEqual(organization.kind, Organization.Kind.VETERINARY)
        self.assertEqual(organization.locality, "Avellaneda")
        self.assertEqual(organization.donation_alias, "veterinaria.parque")
        self.assertFalse(organization.is_verified)
        self.assertTrue(OrganizationMembership.objects.filter(organization=organization, user=user, role="manager").exists())
        self.assertFalse(user.has_perm("patients.view_patient"))
        self.assertFalse(response.json()["organization"]["verified"])

    def test_mobile_dashboard_only_exposes_published_or_resolved_reports(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("panel-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")
        LostPetReport.objects.create(reporter=self.user, name="Luna", species="dog", last_seen_at=timezone.now(), area_label="Centro")
        LostPetReport.objects.create(reporter=self.user, name="Milo", species="cat", last_seen_at=timezone.now(), area_label="Norte", status=LostPetReport.Status.RESOLVED)
        LostPetReport.objects.create(reporter=self.user, name="Oculto", species="dog", last_seen_at=timezone.now(), area_label="Sur", status=LostPetReport.Status.HIDDEN)

        active = self.client.get(reverse("mobile_reports"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        found = self.client.get(reverse("mobile_reports"), {"estado": "encontrados"}, HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        self.assertEqual([item["name"] for item in active.json()["reports"]], ["Luna"])
        self.assertEqual([item["name"] for item in found.json()["reports"]], ["Milo"])

    def test_mobile_my_animals_only_exposes_linked_history_and_can_manage_consent(self):
        roles = ensure_base_roles()
        owner = User.objects.create_user("responsable-movil", password="secret", first_name="Ana")
        owner.groups.add(roles["collaborator"])
        contact = Contact.objects.create(full_name="Ana Responsable")
        linked_patient = Patient.objects.create(name="Luna", species="cat", allergies="Polen")
        other_patient = Patient.objects.create(name="Privado", species="dog")
        PatientContact.objects.create(patient=linked_patient, contact=contact, role="responsible", is_primary=True)
        OwnerAccountLink.objects.create(contact=contact, user=owner)
        ClinicalRecord.objects.create(patient=linked_patient, professional=self.user, reason="Control", notes="Sin novedades")
        raw_token, _ = MobileAccessToken.issue(owner, "Prueba")

        response = self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([animal["name"] for animal in response.json()["animals"]], ["Luna"])
        self.assertEqual(response.json()["animals"][0]["clinical_records"][0]["reason"], "Control")

        response = self.client.post(
            reverse("mobile_my_animal_detail", args=[linked_patient.id]),
            data='{"sharing_enabled": true}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["animal"]["sharing_enabled"])
        self.assertTrue(PatientSharingConsent.objects.get(patient=linked_patient, contact=contact).enabled)
        forbidden = self.client.get(reverse("mobile_my_animal_detail", args=[other_patient.id]), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        self.assertEqual(forbidden.status_code, 404)

    def test_mobile_owner_can_add_animal_and_is_linked_automatically(self):
        roles = ensure_base_roles()
        owner = User.objects.create_user("nueva-responsable", password="secret", first_name="María", last_name="López")
        owner.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(owner, "Prueba")

        response = self.client.post(
            reverse("mobile_my_animals"),
            data={
                "name": "Mora",
                "species": "dog",
                "breed": "Mestiza",
                "birth_date": "2023-04-10",
                "microchip": "AR-123",
                "allergies": "Polen",
                "photo": self.sample_photo(),
            },
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        patient = Patient.objects.get(name="Mora")
        self.assertEqual(patient.species, "dog")
        self.assertTrue(bool(patient.photo))
        self.assertTrue(OwnerAccountLink.objects.filter(user=owner, contact__patientcontact__patient=patient).exists())
        listing = self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        self.assertEqual([animal["name"] for animal in listing.json()["animals"]], ["Mora"])

    def test_mobile_family_code_links_one_patient_without_duplication_and_can_be_revoked(self):
        roles = ensure_base_roles()
        owner = User.objects.create_user("titular-familia", password="secret")
        relative = User.objects.create_user("familiar-familia", password="secret", first_name="Nico")
        owner.groups.add(roles["collaborator"])
        relative.groups.add(roles["collaborator"])
        contact = Contact.objects.create(full_name="Titular")
        patient = Patient.objects.create(name="Kira", species="dog")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        OwnerAccountLink.objects.create(contact=contact, user=owner)
        owner_token, _ = MobileAccessToken.issue(owner, "Titular")
        relative_token, _ = MobileAccessToken.issue(relative, "Familiar")

        invitation = self.client.post(
            reverse("mobile_family_invite_create", args=[patient.id]),
            HTTP_AUTHORIZATION=f"Bearer {owner_token}",
        )
        self.assertEqual(invitation.status_code, 201)
        code = invitation.json()["code"]

        accepted = self.client.post(
            reverse("mobile_family_invite_accept"),
            data=f'{{"code":"{code}"}}',
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {relative_token}",
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(Patient.objects.filter(name="Kira").count(), 1)
        access = PatientFamilyAccess.objects.get(patient=patient, user=relative)
        listing = self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {relative_token}")
        self.assertEqual([animal["name"] for animal in listing.json()["animals"]], ["Kira"])

        revoked = self.client.post(
            reverse("mobile_family_access_revoke", args=[patient.id, access.id]),
            HTTP_AUTHORIZATION=f"Bearer {owner_token}",
        )
        self.assertEqual(revoked.status_code, 200)
        listing = self.client.get(reverse("mobile_my_animals"), HTTP_AUTHORIZATION=f"Bearer {relative_token}")
        self.assertEqual(listing.json()["animals"], [])

    def test_mobile_owner_can_issue_a_temporary_travel_credential(self):
        roles = ensure_base_roles()
        owner = User.objects.create_user("viaje-movil", password="secret")
        owner.groups.add(roles["collaborator"])
        contact = Contact.objects.create(full_name="Nora Responsable")
        patient = Patient.objects.create(name="Mora", species="dog")
        PatientContact.objects.create(patient=patient, contact=contact, role="responsible", is_primary=True)
        OwnerAccountLink.objects.create(contact=contact, user=owner)
        raw_token, _ = MobileAccessToken.issue(owner, "Prueba")

        response = self.client.post(
            reverse("mobile_my_animal_credential", args=[patient.id]),
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["code"])
        self.assertIn("expires_at", response.json())

    def test_mobile_search_request_is_hidden_until_staff_publishes_it(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("solicita-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")

        response = self.client.post(
            reverse("mobile_search_request"),
            data={"name": "Nube", "species": "gato", "area": "Parque central", "description": "Collar rojo", "photo": self.sample_photo()},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        report = LostPetReport.objects.get(name="Nube")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(report.status, LostPetReport.Status.HIDDEN)
        self.assertEqual(report.reporter, collaborator)
        self.assertTrue(report.requested_via_mobile)
        self.assertTrue(bool(report.photo))

    def test_mobile_request_owner_can_edit_pending_or_rejected_request(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("edita-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")
        report = LostPetReport.objects.create(
            reporter=collaborator,
            name="Nube",
            species="cat",
            last_seen_at=timezone.now(),
            area_label="Centro",
            requested_via_mobile=True,
            status=LostPetReport.Status.REJECTED,
            review_note="Necesitamos confirmar la zona.",
        )

        response = self.client.post(
            reverse("mobile_search_request_edit", args=[report.id]),
            data={"name": "Nube", "species": "gato", "area": "Parque central", "description": "Collar rojo", "photo": self.sample_photo()},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

        report.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(report.status, LostPetReport.Status.HIDDEN)
        self.assertEqual(report.review_note, "")
        self.assertEqual(report.area_label, "Parque central")
        self.assertTrue(bool(report.photo))

    def test_staff_can_accept_or_reject_a_mobile_request_with_feedback(self):
        collaborator = User.objects.create_user("solicita-revision", password="secret")
        report = LostPetReport.objects.create(
            reporter=collaborator,
            name="Mora",
            species="dog",
            last_seen_at=timezone.now(),
            area_label="Centro",
            requested_via_mobile=True,
            status=LostPetReport.Status.HIDDEN,
        )

        rejected = self.client.post(reverse("lost_pet_change_status", args=[report.id]), {"status": "rejected", "review_note": "Necesitamos una foto donde se vea mejor."})
        report.refresh_from_db()
        self.assertRedirects(rejected, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(report.status, LostPetReport.Status.REJECTED)
        self.assertEqual(report.review_note, "Necesitamos una foto donde se vea mejor.")
        self.assertTrue(CommunityNotification.objects.filter(recipient=collaborator, report=report, title__icontains="rechazada").exists())

        accepted = self.client.post(reverse("lost_pet_change_status", args=[report.id]), {"status": "published"})
        report.refresh_from_db()
        self.assertRedirects(accepted, reverse("lost_pet_detail", args=[report.id]))
        self.assertEqual(report.status, LostPetReport.Status.PUBLISHED)
        self.assertEqual(report.review_note, "")
        self.assertTrue(CommunityNotification.objects.filter(recipient=collaborator, report=report, title__icontains="publicada").exists())

    def test_community_adoption_needs_staff_approval_before_being_public(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("adopta-colabora", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")
        response = self.client.post(
            reverse("mobile_adoption_request"),
            data={"name": "Kira", "species": "perro", "area": "Barrio Norte", "age": "2 años", "photo": self.sample_photo()},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )
        post = AdoptionPost.objects.get(name="Kira")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(post.status, AdoptionPost.Status.PENDING)
        self.assertEqual(self.client.get(reverse("mobile_adoptions"), HTTP_AUTHORIZATION=f"Bearer {raw_token}").json()["adoptions"], [])

        self.user.user_permissions.add(*Permission.objects.filter(codename__in=["view_adoptionpost", "change_adoptionpost"]))
        approved = self.client.post(reverse("adoption_change_status", args=[post.id]), {"status": "published"})
        post.refresh_from_db()
        self.assertRedirects(approved, reverse("adoption_list"))
        self.assertEqual(post.status, AdoptionPost.Status.PUBLISHED)
        self.assertEqual([item["name"] for item in self.client.get(reverse("mobile_adoptions"), HTTP_AUTHORIZATION=f"Bearer {raw_token}").json()["adoptions"]], ["Kira"])

    def test_adoption_interest_is_private_and_requires_staff_management(self):
        roles = ensure_base_roles()
        collaborator = User.objects.create_user("quiere-adoptar", password="secret")
        collaborator.groups.add(roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(collaborator, "Prueba")
        post = AdoptionPost.objects.create(publisher=self.user, name="Kira", species="dog", area_label="Centro", status=AdoptionPost.Status.PUBLISHED)

        response = self.client.post(reverse("mobile_adoption_interest", args=[post.id]), data='{"message":"Tengo experiencia y un hogar preparado para recibirla."}', content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        interest = AdoptionInterest.objects.get(post=post, applicant=collaborator)
        duplicate = self.client.post(reverse("mobile_adoption_interest", args=[post.id]), data='{"message":"Quiero adoptar a Kira."}', content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {raw_token}")
        activity = self.client.get(reverse("mobile_my_adoption_interests"), HTTP_AUTHORIZATION=f"Bearer {raw_token}")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(interest.status, AdoptionInterest.Status.RECEIVED)
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(activity.json()["interests"][0]["animal_name"], "Kira")


class ShelterAdoptionPublishingTests(TestCase):
    def setUp(self):
        roles = ensure_base_roles()
        self.manager = User.objects.create_user("refugio-manager", password="secret")
        self.manager.groups.add(roles["collaborator"])
        self.shelter = Organization.objects.create(name="Patitas Rescatadas", kind="shelter", is_verified=True)
        OrganizationMembership.objects.create(organization=self.shelter, user=self.manager, role=OrganizationMembership.Role.MANAGER)
        self.client.force_login(self.manager)

    def test_verified_shelter_manager_can_publish_its_own_adoption(self):
        response = self.client.post(
            reverse("adoption_create"),
            {"name": "Lola", "species": "dog", "breed": "Mestiza", "age_label": "2 años", "description": "Rescatada y lista para un hogar.", "area_label": "Avellaneda"},
        )
        post = AdoptionPost.objects.get(name="Lola")
        self.assertRedirects(response, reverse("adoption_list"))
        self.assertEqual(post.organization, self.shelter)
        self.assertEqual(post.publisher, self.manager)
        self.assertEqual(post.status, AdoptionPost.Status.PUBLISHED)

    def test_pending_shelter_cannot_publish_until_verified(self):
        self.shelter.is_verified = False
        self.shelter.save(update_fields=["is_verified"])
        self.assertEqual(self.client.get(reverse("adoption_create")).status_code, 403)


class MobileAdoptionPublishingAuthorizationTests(TestCase):
    """Only a verified shelter manager may publish from the mobile API."""

    def setUp(self):
        self.roles = ensure_base_roles()

    def request_as(self, user, organization, name):
        user.groups.add(self.roles["collaborator"])
        raw_token, _ = MobileAccessToken.issue(user, "Authorization regression")
        return self.client.post(
            reverse("mobile_adoption_request"),
            data={"name": name, "species": "perro", "area": "Centro", "organization_id": organization.id},
            HTTP_AUTHORIZATION=f"Bearer {raw_token}",
        )

    def test_only_verified_shelter_manager_publishes_immediately(self):
        verified_shelter = Organization.objects.create(name="Refugio verificado", kind=Organization.Kind.SHELTER, is_verified=True)
        unverified_shelter = Organization.objects.create(name="Refugio pendiente", kind=Organization.Kind.SHELTER, is_verified=False)
        veterinary = Organization.objects.create(name="Veterinaria verificada", kind=Organization.Kind.VETERINARY, is_verified=True)

        manager = User.objects.create_user("shelter-manager", password="secret")
        staff = User.objects.create_user("shelter-staff", password="secret")
        pending_manager = User.objects.create_user("pending-manager", password="secret")
        veterinary_manager = User.objects.create_user("vet-manager", password="secret")
        OrganizationMembership.objects.create(organization=verified_shelter, user=manager, role=OrganizationMembership.Role.MANAGER)
        OrganizationMembership.objects.create(organization=verified_shelter, user=staff, role=OrganizationMembership.Role.STAFF)
        OrganizationMembership.objects.create(organization=unverified_shelter, user=pending_manager, role=OrganizationMembership.Role.MANAGER)
        OrganizationMembership.objects.create(organization=veterinary, user=veterinary_manager, role=OrganizationMembership.Role.MANAGER)

        self.assertEqual(self.request_as(manager, verified_shelter, "Lola").status_code, 201)
        self.assertEqual(AdoptionPost.objects.get(name="Lola").status, AdoptionPost.Status.PUBLISHED)

        for user, organization, name in [
            (staff, verified_shelter, "Toto"),
            (pending_manager, unverified_shelter, "Mora"),
            (veterinary_manager, veterinary, "Nube"),
        ]:
            self.assertEqual(self.request_as(user, organization, name).status_code, 201)
            self.assertEqual(AdoptionPost.objects.get(name=name).status, AdoptionPost.Status.PENDING)


class MobileShelterCaregiverTests(TestCase):
    def setUp(self):
        roles = ensure_base_roles()
        self.manager = User.objects.create_user("shelter-owner")
        self.caregiver = User.objects.create_user("caregiver")
        for user in (self.manager, self.caregiver):
            user.groups.add(roles["collaborator"])
        self.shelter = Organization.objects.create(name="Refugio", kind="shelter", is_verified=True)
        self.membership = OrganizationMembership.objects.create(organization=self.shelter, user=self.manager, role="manager")
        self.patient = Patient.objects.create(name="Luna", species="dog", organization=self.shelter)
        self.other = Patient.objects.create(name="Otra", species="cat", organization=Organization.objects.create(name="Otro", kind="shelter", is_verified=True))
        self.manager_token, _ = MobileAccessToken.issue(self.manager, "test")
        self.caregiver_token, _ = MobileAccessToken.issue(self.caregiver, "test")

    def request_as(self, token, route, args=(), data=None):
        url = reverse(route, args=args)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        if data is None:
            return self.client.get(url, **headers)
        return self.client.post(url, data=data, content_type="application/json", **headers)

    def invite(self):
        response = self.request_as(self.manager_token, "mobile_family_invite_create", [self.patient.id], {})
        self.assertEqual(response.status_code, 201)
        return response.json()["code"]

    def test_manager_shares_only_own_shelter_and_caregiver_access_is_revocable(self):
        listing = self.request_as(self.manager_token, "mobile_my_animals").json()["animals"]
        self.assertEqual([item["id"] for item in listing], [self.patient.id])
        self.assertTrue(listing[0]["can_invite_caregiver"])
        self.assertFalse(listing[0]["can_share_with_family"])
        self.assertEqual(self.request_as(self.manager_token, "mobile_family_invite_create", [self.other.id], {}).status_code, 404)
        code = self.invite()
        result = self.request_as(self.caregiver_token, "mobile_family_invite_accept", data={"code": code})
        self.assertEqual(result.status_code, 201)
        self.assertFalse(result.json()["animal"]["can_invite_caregiver"])
        self.assertEqual(self.request_as(self.caregiver_token, "mobile_family_invite_create", [self.patient.id], {}).status_code, 403)
        self.assertEqual(self.request_as(self.caregiver_token, "mobile_family_invite_accept", data={"code": code}).status_code, 400)
        access = PatientFamilyAccess.objects.get(patient=self.patient, user=self.caregiver)
        self.assertEqual(self.request_as(self.manager_token, "mobile_family_access_revoke", [self.patient.id, access.id], {}).status_code, 200)
        self.assertEqual(self.request_as(self.caregiver_token, "mobile_my_animal_detail", [self.patient.id]).status_code, 404)

    def test_pending_shelter_or_staff_cannot_invite_or_list_institutional_patients(self):
        self.membership.role = "staff"
        self.membership.save()
        self.assertEqual(self.request_as(self.manager_token, "mobile_my_animals").json()["animals"], [])
        self.assertEqual(self.request_as(self.manager_token, "mobile_family_invite_create", [self.patient.id], {}).status_code, 404)
        self.membership.role = "manager"
        self.membership.save()
        self.shelter.is_verified = False
        self.shelter.save()
        self.assertEqual(self.request_as(self.manager_token, "mobile_family_invite_create", [self.patient.id], {}).status_code, 404)

    def test_removed_manager_cannot_leave_a_redeemable_invitation(self):
        code = self.invite()
        self.membership.delete()
        self.assertEqual(self.request_as(self.caregiver_token, "mobile_family_invite_accept", data={"code": code}).status_code, 400)

    def test_shelter_invitation_permission_does_not_grant_travel_consent(self):
        self.assertEqual(self.request_as(self.manager_token, "mobile_my_animal_credential", [self.patient.id], {}).status_code, 403)
        self.assertEqual(self.request_as(self.manager_token, "mobile_my_animal_detail", [self.patient.id], {"sharing_enabled": True}).status_code, 403)


class CommunityAdoptionBrowsingTests(TestCase):
    def setUp(self):
        roles = ensure_base_roles()
        self.user = User.objects.create_user("adoption-reader")
        self.user.groups.add(roles["collaborator"])
        self.shelter = Organization.objects.create(name="Refugio lector", kind="shelter", is_verified=True)
        self.published = AdoptionPost.objects.create(publisher=self.user, organization=self.shelter, name="Visible", species="dog", area_label="Centro", status="published")
        self.pending = AdoptionPost.objects.create(publisher=self.user, organization=self.shelter, name="Privada pendiente", species="cat", area_label="Centro", status="pending")
        self.client.force_login(self.user)

    def test_community_can_browse_only_published_posts_even_with_management_filters(self):
        for mode in ("published", "review", "all"):
            response = self.client.get(reverse("adoption_list"), {"view": mode})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(list(response.context["posts"]), [self.published])
            self.assertFalse(response.context["can_manage_adoptions"])
            self.assertNotContains(response, "Aprobar y publicar")
            self.assertNotContains(response, "Publicar animal")

    def test_read_access_does_not_allow_creation_or_status_changes(self):
        self.assertEqual(self.client.get(reverse("adoption_create")).status_code, 403)
        for organization in (self.shelter, None):
            self.published.organization = organization
            self.published.save()
            response = self.client.post(reverse("adoption_change_status", args=[self.published.id]), {"status": "adopted"})
            self.assertEqual(response.status_code, 403)
            self.published.refresh_from_db()
            self.assertEqual(self.published.status, "published")

    def test_login_and_community_permission_remain_required(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("adoption_list")).status_code, 302)
        unrelated = User.objects.create_user("without-community-permission")
        self.client.force_login(unrelated)
        self.assertEqual(self.client.get(reverse("adoption_list")).status_code, 403)


class WebAdoptionInterestTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("web-adopter")
        self.user.groups.add(ensure_base_roles()["collaborator"])
        self.publisher = User.objects.create_user("publisher")
        self.post = AdoptionPost.objects.create(publisher=self.publisher, name="Mora", species="dog", area_label="Centro", status="published")
        self.url = reverse("adoption_interest_create", args=[self.post.id])
        self.client.force_login(self.user)

    def test_card_opens_form_and_submission_is_private_and_not_duplicated(self):
        self.assertContains(self.client.get(reverse("adoption_list")), self.url)
        self.assertContains(self.client.get(self.url), "Enviar mi interés")
        message = "Tengo un hogar preparado para recibir a Mora."
        self.assertRedirects(self.client.post(self.url, {"message": message}), self.url)
        interest = AdoptionInterest.objects.get(post=self.post, applicant=self.user)
        self.assertEqual(interest.message, message)
        self.client.post(self.url, {"message": "Otro mensaje suficientemente largo"})
        self.assertEqual(AdoptionInterest.objects.filter(post=self.post).count(), 1)
        self.assertContains(self.client.get(self.url), "Tu interés ya está registrado")
        self.assertNotContains(self.client.get(reverse("adoption_list")), message)
        self.client.force_login(self.publisher)
        self.publisher.groups.add(ensure_base_roles()["collaborator"])
        self.assertNotContains(self.client.get(self.url), message)

    def test_invalid_messages_and_unpublished_animals_do_not_create_interest(self):
        for message in ("", "corto", "x" * 701):
            self.assertContains(self.client.post(self.url, {"message": message}), "entre 10 y 700")
        self.assertFalse(AdoptionInterest.objects.exists())
        self.post.status = "pending"
        self.post.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, {"message": "Quiero conocer a Mora"}).status_code, 404)

    def test_login_and_csrf_protect_submission(self):
        from django.test import Client
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        self.assertEqual(csrf_client.post(self.url, {"message": "Quiero conocer a Mora"}).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class MyAdoptionInterestsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("my-requests")
        self.other = User.objects.create_user("other-requests")
        self.user.groups.add(ensure_base_roles()["collaborator"])
        self.post = AdoptionPost.objects.create(publisher=self.other, name="Mora", species="dog", area_label="Centro", status="published")
        self.url = reverse("my_adoption_interests")
        self.client.force_login(self.user)

    def test_own_requests_and_replies_remain_visible_after_archiving(self):
        own = AdoptionInterest.objects.create(post=self.post, applicant=self.user, message="Mi solicitud privada", staff_note="Podemos coordinar una visita", status="contact")
        AdoptionInterest.objects.create(post=self.post, applicant=self.other, message="Mensaje privado de otra persona", staff_note="Respuesta de otra persona")
        self.post.status = "archived"
        self.post.save()
        response = self.client.get(self.url, {"applicant": self.other.id})
        self.assertEqual(list(response.context["interests"]), [own])
        for value in ("Mora", "Mi solicitud privada", "Podemos coordinar una visita", "En conversación", "archivado"):
            self.assertContains(response, value)
        self.assertNotContains(response, "Mensaje privado de otra persona")
        self.assertNotContains(response, "Respuesta de otra persona")

    def test_empty_state_and_links_after_submission(self):
        self.assertContains(self.client.get(self.url), "Todavía no enviaste solicitudes")
        self.assertContains(self.client.get(reverse("adoption_list")), self.url)
        self.assertContains(self.client.get(reverse("lost_pet_list")), self.url)
        response = self.client.post(reverse("adoption_interest_create", args=[self.post.id]), {"message": "Me interesa conocer a Mora"}, follow=True)
        self.assertContains(response, self.url)
        self.assertContains(self.client.get(self.url), "Me interesa conocer a Mora")

    def test_anonymous_access_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AdoptionVisitTests(TestCase):
    def setUp(self):
        roles = ensure_base_roles()
        self.applicant = User.objects.create_user("visit-applicant", email="applicant@example.com")
        self.manager = User.objects.create_user("visit-manager", email="manager@example.com")
        self.outsider = User.objects.create_user("visit-outsider")
        for user in (self.applicant, self.manager, self.outsider):
            user.groups.add(roles["collaborator"])
        self.shelter = Organization.objects.create(name="Refugio visitas", kind="shelter", is_verified=True, address="Calle privada 123", locality="Avellaneda")
        OrganizationMembership.objects.create(user=self.manager, organization=self.shelter, role="manager")
        self.post = AdoptionPost.objects.create(publisher=self.manager, organization=self.shelter, name="Mora", species="dog", area_label="Centro", status="published")
        self.interest = AdoptionInterest.objects.create(post=self.post, applicant=self.applicant, message="Quiero conocer a Mora")
        self.request_url = reverse("adoption_visit_request", args=[self.interest.id])
        self.respond_url = reverse("adoption_visit_respond", args=[self.interest.id])

    def test_request_accept_and_private_location(self):
        self.client.force_login(self.applicant)
        self.assertContains(self.client.get(reverse("my_adoption_interests")), "Coordinar visita")
        self.assertNotContains(self.client.get(reverse("my_adoption_interests")), self.shelter.address)

        self.client.post(self.request_url)
        self.interest.refresh_from_db()
        requested_at = self.interest.visit_requested_at
        self.assertEqual(self.interest.visit_status, "requested")
        self.client.post(self.request_url)
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_requested_at, requested_at)
        self.assertNotContains(self.client.get(reverse("my_adoption_interests")), self.shelter.address)
        self.client.force_login(self.manager)
        self.assertContains(self.client.get(reverse("adoption_interest_list")), "Aceptar visita y compartir ubicación")
        self.client.post(self.respond_url, {"action": "accept", "visit_address": "Calle privada 123, Avellaneda", "visit_instructions": "Sábado a las 10"})
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "accepted")
        self.client.force_login(self.applicant)
        response = self.client.get(reverse("my_adoption_interests"))
        self.assertContains(response, "Calle privada 123, Avellaneda")
        self.assertContains(response, "Sábado a las 10")
        self.assertContains(response, "https://www.google.com/maps/search/")
        self.assertNotContains(self.client.get(reverse("adoption_list")), self.shelter.address)
        self.client.force_login(self.outsider)
        self.assertNotContains(self.client.get(reverse("my_adoption_interests")), self.shelter.address)

    def test_shelter_lands_on_received_requests_and_only_sees_own_animals(self):
        other_shelter = Organization.objects.create(name="Other refuge", kind="shelter", is_verified=True)
        other_post = AdoptionPost.objects.create(publisher=self.outsider, organization=other_shelter, name="Private animal", species="dog", status="published")
        AdoptionInterest.objects.create(post=other_post, applicant=self.outsider, message="Other private request", visit_status="requested")
        self.client.force_login(self.manager)
        self.assertRedirects(self.client.get(reverse("dashboard")), reverse("adoption_interest_list"))
        response = self.client.get(reverse("adoption_interest_list"))
        self.assertContains(response, "Solicitudes recibidas")
        self.assertContains(response, self.interest.message)
        self.assertNotContains(response, "Other private request")
        self.assertEqual(response.context["counts"], {"total": 1, "received": 1, "visits": 0})
        response = self.client.get(reverse("adoption_interest_list"), {"view": "visits"})
        self.assertEqual(list(response.context["interests"]), [])
        self.interest.visit_status = "requested"
        self.interest.save()
        response = self.client.get(reverse("adoption_interest_list"), {"view": "visits"})
        self.assertEqual(list(response.context["interests"]), [self.interest])
        response = self.client.get(reverse("adoption_list"))
        self.assertContains(response, "Solicitudes recibidas")
        self.assertNotContains(response, "Quiero conocer a Mora")
        self.client.force_login(self.applicant)
        self.assertEqual(self.client.get(reverse("adoption_interest_list")).status_code, 403)

    def test_other_accounts_cannot_request_or_answer(self):
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.request_url).status_code, 404)
        self.assertEqual(self.client.post(self.respond_url, {"action": "accept", "visit_address": "Ajena"}).status_code, 404)
        self.client.force_login(self.applicant)
        self.assertEqual(self.client.post(self.respond_url, {"action": "accept", "visit_address": "Ajena"}).status_code, 404)
        self.assertEqual(self.client.get(self.request_url).status_code, 405)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_recipients_privacy_and_duplicate_actions(self):
        for username, email, active, role in (
            ("duplicate", "MANAGER@example.com", True, "manager"),
            ("inactive", "inactive@example.com", False, "manager"),
            ("staff", "staff@example.com", True, "staff"),
            ("invalid", "invalid", True, "manager"),
        ):
            user = User.objects.create_user(username, email=email, is_active=active)
            OrganizationMembership.objects.create(user=user, organization=self.shelter, role=role)
        self.client.force_login(self.applicant)
        self.client.post(self.request_url)
        self.client.post(self.request_url)
        self.assertEqual(len(mail.outbox), 1)
        alert = mail.outbox[0]
        self.assertEqual(alert.bcc, ["manager@example.com"])
        self.assertEqual(alert.to, [])
        self.assertIn("http://testserver" + reverse("adoption_interest_list"), alert.body)
        self.assertIn("Mora", alert.body)
        self.client.force_login(self.manager)
        data = {"action": "accept", "visit_address": self.shelter.address, "visit_instructions": "Sábado a las 10"}
        self.client.post(self.respond_url, data)
        self.client.post(self.respond_url, data)
        self.assertEqual(len(mail.outbox), 2)
        reply = mail.outbox[1]
        self.assertEqual(reply.bcc, ["applicant@example.com"])
        self.assertIn("Visita aceptada", reply.subject)
        self.assertIn("http://testserver" + reverse("my_adoption_interests"), reply.body)
        for message in mail.outbox:
            self.assertNotIn(self.shelter.address, message.body)
            self.assertNotIn("Sábado a las 10", message.body)

    def test_declined_visit_sends_response_email(self):
        self.client.force_login(self.applicant)
        self.client.post(self.request_url)
        self.client.force_login(self.manager)
        self.client.post(self.respond_url, {"action": "decline"})
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("no pudo aceptar", mail.outbox[-1].body)

    def test_email_failure_preserves_request_and_response_without_logging_secrets(self):
        with patch("lost_pets.adoption_email.EmailMessage.send", side_effect=OSError("private SMTP detail")):
            with self.assertLogs("lost_pets.adoption_email", level="WARNING") as logs:
                self.client.force_login(self.applicant)
                response = self.client.post(self.request_url, follow=True)
                self.assertContains(response, "no pudimos enviar")
                self.interest.refresh_from_db()
                self.assertEqual(self.interest.visit_status, "requested")
                self.client.force_login(self.manager)
                response = self.client.post(self.respond_url, {"action": "decline"}, follow=True)
                self.assertContains(response, "no pudimos enviar")
                self.interest.refresh_from_db()
                self.assertEqual(self.interest.visit_status, "declined")
            self.assertNotIn("private SMTP detail", str(logs.output))

    def test_missing_email_preserves_visit_and_warns(self):
        self.manager.email = ""
        self.manager.save()
        self.client.force_login(self.applicant)
        response = self.client.post(self.request_url, follow=True)
        self.assertContains(response, "no pudimos enviar")
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "requested")
        self.assertEqual(len(mail.outbox), 0)

    def test_accept_requires_request_and_address_and_decline_hides_address(self):
        self.client.force_login(self.manager)
        self.client.post(self.respond_url, {"action": "accept", "visit_address": "Calle privada 123"})
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "none")
        self.client.force_login(self.applicant)
        self.client.post(self.request_url)
        self.client.force_login(self.manager)
        self.client.post(self.respond_url, {"action": "accept", "visit_address": ""})
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "requested")
        self.client.post(self.respond_url, {"action": "decline", "visit_address": "No divulgar", "visit_instructions": "No hay disponibilidad"})
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "declined")
        self.assertEqual(self.interest.visit_address, "")
        self.client.force_login(self.applicant)
        response = self.client.get(reverse("my_adoption_interests"))
        self.assertContains(response, "No hay disponibilidad")
        self.assertNotContains(response, "No divulgar")

    def test_archived_post_cannot_request_visit(self):
        self.post.status = "archived"
        self.post.save()
        self.client.force_login(self.applicant)
        self.client.post(self.request_url)
        self.interest.refresh_from_db()
        self.assertEqual(self.interest.visit_status, "none")
        self.assertEqual(len(mail.outbox), 0)
