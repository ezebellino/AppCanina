"""Ownership requires both an explicit grant and the matching contact relation."""
from django.db.models import F

from .models import OwnerAccountLink, PatientContact


def owner_relations(user):
    # Keep these predicates in one filter: they must match the SAME link.
    return PatientContact.objects.filter(
        contact__account_links__user=user,
        contact__account_links__patients=F('patient_id'),
        role__in=[PatientContact.Role.RESPONSIBLE, PatientContact.Role.ADOPTER],
    ).distinct()


def owner_contact_ids(user, patient):
    return owner_relations(user).filter(patient=patient).values_list('contact_id', flat=True)


def grant_ownership(user, contact, patient):
    link, _ = OwnerAccountLink.objects.get_or_create(user=user, contact=contact)
    link.patients.add(patient)
    return link
