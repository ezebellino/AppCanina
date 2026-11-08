"""Household invitations shared by web and mobile clients."""
import hashlib

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from organizations.models import OrganizationMembership
from .models import Contact, OwnerAccountLink, Patient, PatientContact, PatientFamilyAccess, PatientFamilyInvite


def owned_animals(user):
    contacts = OwnerAccountLink.objects.filter(user=user).values_list("contact_id", flat=True)
    return Patient.objects.filter(active=True).filter(
        Q(patientcontact__contact_id__in=contacts,
          patientcontact__role__in=[PatientContact.Role.RESPONSIBLE, PatientContact.Role.ADOPTER])
        | Q(family_accesses__user=user, family_accesses__revoked_at__isnull=True)
    ).distinct()


def can_invite(user, patient):
    contacts = OwnerAccountLink.objects.filter(user=user).values_list("contact_id", flat=True)
    return patient.patientcontact_set.filter(contact_id__in=contacts, role=PatientContact.Role.RESPONSIBLE).exists() or OrganizationMembership.objects.filter(
        user=user, organization_id=patient.organization_id, role="manager",
        organization__kind="shelter", organization__is_verified=True,
    ).exists()


@transaction.atomic
def accept_invitation(user, code):
    digest = hashlib.sha256(code.strip().encode()).hexdigest()
    invite = PatientFamilyInvite.objects.select_for_update().select_related("patient", "invited_by").filter(digest=digest).first()
    if (not invite or not invite.is_active or not invite.patient.active
            or not invite.invited_by.is_active or not can_invite(invite.invited_by, invite.patient)):
        raise ValueError("El código no es válido, ya fue utilizado o venció.")
    if invite.invited_by_id == user.id:
        raise ValueError("No podés usar tu propio código familiar.")
    # Conditional update also prevents double consumption on SQLite.
    if not PatientFamilyInvite.objects.filter(pk=invite.pk, accepted_at__isnull=True, revoked_at__isnull=True).update(accepted_by=user, accepted_at=timezone.now()):
        raise ValueError("El código ya fue utilizado.")
    link = OwnerAccountLink.objects.filter(user=user).select_related("contact").first()
    if link:
        contact = link.contact
    else:
        contact = Contact.objects.create(full_name=user.get_full_name().strip() or user.username)
        OwnerAccountLink.objects.create(user=user, contact=contact)
    PatientContact.objects.get_or_create(patient=invite.patient, contact=contact, role=PatientContact.Role.CUSTODIAN, defaults={"is_primary": False})
    PatientFamilyAccess.objects.update_or_create(patient=invite.patient, user=user, defaults={
        "contact": contact, "granted_by": invite.invited_by, "invitation": invite, "revoked_at": None,
    })
    return invite.patient
