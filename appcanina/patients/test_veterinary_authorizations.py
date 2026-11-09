from datetime import timedelta

from django.contrib.auth.models import Permission, User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from organizations.models import Organization, OrganizationMembership
from .models import (ClinicalRecord, Contact, Patient, PatientContact, PatientFamilyAccess,
                     PatientSharingConsent, TravelAccessRequest, TravelCredential,
                     VeterinaryAuthorization, VeterinaryAccessLog)
from .ownership import grant_ownership


class VeterinaryAuthorizationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner')
        self.vet = User.objects.create_user('vet')
        self.other = User.objects.create_user('other')
        perms = Permission.objects.filter(content_type__app_label='patients', codename__in=['view_clinicalrecord', 'add_clinicalrecord'])
        self.vet.user_permissions.add(*perms)
        self.other.user_permissions.add(*perms)
        self.org = Organization.objects.create(name='Verified vet', kind='veterinary', is_verified=True, locality='City')
        self.other_org = Organization.objects.create(name='Other vet', kind='veterinary', is_verified=True)
        self.membership = OrganizationMembership.objects.create(user=self.vet, organization=self.org)
        OrganizationMembership.objects.create(user=self.other, organization=self.other_org)
        self.pet = Patient.objects.create(name='Evaristo', species='dog')
        self.contact = Contact.objects.create(full_name='Owner')
        PatientContact.objects.create(patient=self.pet, contact=self.contact, role='responsible')
        grant_ownership(self.owner, self.contact, self.pet)
        self.grant = VeterinaryAuthorization.objects.create(patient=self.pet, organization=self.org,
            granted_by=self.owner, mode='attend', expires_at=timezone.now() + timedelta(hours=24))
        self.url = reverse('veterinary_authorized_history', args=[self.grant.pk])
        self.owner_url = reverse('veterinary_authorizations', args=[self.pet.pk])
        self.revoke_url = reverse('veterinary_authorization_revoke', args=[self.pet.pk, self.grant.pk])
        self.data = {'occurred_on': timezone.localdate().isoformat(), 'reason': 'Vaccination', 'notes': 'Clinical note'}

    def test_owner_can_authorize_verified_vet_and_replace_broader_permission(self):
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(reverse('my_animal_history', args=[self.pet.pk])), 'Autorizar veterinaria')
        response = self.client.post(self.owner_url, {'organization': self.org.pk, 'mode': 'read', 'hours': 24})
        self.assertEqual(response.status_code, 302)
        self.grant.refresh_from_db()
        self.assertIsNotNone(self.grant.revoked_at)
        newest = VeterinaryAuthorization.objects.latest('pk')
        self.assertEqual(newest.granted_by, self.owner)
        self.assertTrue(newest.is_active)
        self.assertEqual(newest.mode, 'read')

    def test_unverified_institution_and_unbounded_duration_rejected(self):
        pending = Organization.objects.create(name='Pending', kind='veterinary')
        shelter = Organization.objects.create(name='Shelter', kind='shelter', is_verified=True)
        self.client.force_login(self.owner)
        for org, hours in [(pending, 24), (shelter, 24), (self.org, 999999)]:
            response = self.client.post(self.owner_url, {'organization': org.pk, 'mode': 'attend', 'hours': hours})
            self.assertEqual(response.status_code, 200)
        self.assertEqual(VeterinaryAuthorization.objects.count(), 1)

    def test_caregiver_and_stranger_cannot_grant_or_revoke(self):
        PatientFamilyAccess.objects.create(patient=self.pet, user=self.other, contact=self.contact, granted_by=self.owner)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.owner_url).status_code, 404)
        self.assertEqual(self.client.post(self.revoke_url).status_code, 404)

    def test_vet_can_append_with_server_set_patient_author_and_institution(self):
        self.client.force_login(self.vet)
        self.assertContains(self.client.get(reverse('veterinary_authorized_patients')), self.pet.name)
        self.assertContains(self.client.get(self.url), 'Guardar atención')
        self.assertEqual(VeterinaryAccessLog.objects.filter(authorization=self.grant).count(), 1)
        response = self.client.post(self.url, {**self.data, 'professional': self.other.pk,
            'patient': 99999, 'organization': self.other_org.pk, 'authorization': 99999})
        self.assertEqual(response.status_code, 302)
        record = ClinicalRecord.objects.get()
        self.assertEqual((record.patient, record.professional, record.organization, record.authorization),
                         (self.pet, self.vet, self.org, self.grant))
        self.client.force_login(self.owner)
        response = self.client.get(reverse('my_animal_history', args=[self.pet.pk]))
        self.assertContains(response, 'Vaccination')
        self.assertContains(response, self.org.name)

    def test_read_only_and_clinical_role_are_enforced_on_post(self):
        self.grant.mode = 'read'
        self.grant.save()
        self.client.force_login(self.vet)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.grant.mode = 'attend'
        self.grant.save()
        self.vet.user_permissions.remove(Permission.objects.get(codename='add_clinicalrecord'))
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertFalse(ClinicalRecord.objects.exists())

    def test_other_institution_cannot_read_or_append(self):
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('veterinary_authorized_patients')), self.pet.name)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)

    def test_revocation_blocks_stale_page_submission_and_preserves_records(self):
        self.client.force_login(self.vet)
        self.client.post(self.url, self.data)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.revoke_url).status_code, 405)
        self.assertEqual(self.client.post(self.revoke_url).status_code, 302)
        self.client.force_login(self.vet)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)
        self.assertEqual(ClinicalRecord.objects.count(), 1)

    def test_expiration_membership_and_verification_are_rechecked(self):
        self.client.force_login(self.vet)
        self.grant.expires_at = timezone.now() - timedelta(seconds=1)
        self.grant.save()
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)
        self.grant.expires_at = timezone.now() + timedelta(days=1)
        self.grant.save()
        self.org.is_verified = False
        self.org.save()
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.org.is_verified = True
        self.org.save()
        self.membership.delete()
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)

    def test_lost_owner_authority_disables_grant(self):
        self.contact.account_links.get(user=self.owner).patients.clear()
        self.client.force_login(self.vet)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 404)

    def test_append_does_not_edit_prior_record_or_grant_normal_staff_access(self):
        existing = ClinicalRecord.objects.create(patient=self.pet, professional=self.other, reason='Original', notes='Keep')
        self.client.force_login(self.vet)
        self.client.post(self.url, {**self.data, 'id': existing.pk})
        existing.refresh_from_db()
        self.assertEqual(existing.reason, 'Original')
        self.assertEqual(ClinicalRecord.objects.count(), 2)
        self.assertEqual(self.client.post(reverse('clinical_record_create', args=[self.pet.pk]), self.data).status_code, 404)

    def test_csrf_and_private_cache(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.revoke_url).status_code, 403)
        client.force_login(self.vet)
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        self.assertIn('no-store', client.get(self.url)['Cache-Control'])

    def test_legacy_travel_access_rechecks_consent_and_credentials(self):
        consent = PatientSharingConsent.objects.create(patient=self.pet, contact=self.contact, enabled=True)
        _, credential = TravelCredential.issue(self.pet, self.contact, timezone.now() + timedelta(days=1))
        access = TravelAccessRequest.objects.create(patient=self.pet, credential=credential, organization=self.org,
            requester=self.vet, locality='City', purpose='Visit', status='approved', expires_at=credential.expires_at)
        url = reverse('travel_access_history', args=[access.pk])
        self.client.force_login(self.vet)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.owner)
        self.client.post(reverse('my_animal_sharing', args=[self.pet.pk]), {})
        self.client.force_login(self.vet)
        self.assertEqual(self.client.get(url).status_code, 302)
        consent.refresh_from_db()
        consent.enabled = True
        consent.save()
        self.assertEqual(self.client.get(url).status_code, 302)
        credential.refresh_from_db()
        self.assertIsNotNone(credential.revoked_at)
