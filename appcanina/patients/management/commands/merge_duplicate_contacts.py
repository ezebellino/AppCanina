from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from patients.models import Contact, PatientContact
from sales.models import Sale


class Command(BaseCommand):
    help = "Consolida contactos idénticos (nombre, tipo, teléfono y correo) preservando vínculos y ventas."

    def handle(self, *args, **options):
        duplicate_groups = Contact.objects.values("full_name", "kind", "phone", "email").annotate(total=Count("id")).filter(total__gt=1)
        merged = 0
        with transaction.atomic():
            for group in duplicate_groups:
                contacts = list(Contact.objects.filter(**{key: group[key] for key in ("full_name", "kind", "phone", "email")}).order_by("id"))
                canonical, duplicates = contacts[0], contacts[1:]
                for duplicate in duplicates:
                    for relation in PatientContact.objects.filter(contact=duplicate):
                        existing = PatientContact.objects.filter(patient=relation.patient, contact=canonical, role=relation.role).first()
                        if existing:
                            if relation.is_primary and not existing.is_primary:
                                existing.is_primary = True
                                existing.save(update_fields=["is_primary"])
                            relation.delete()
                        else:
                            relation.contact = canonical
                            relation.save(update_fields=["contact"])
                    Sale.objects.filter(contact=duplicate).update(contact=canonical)
                    duplicate.delete()
                    merged += 1
        self.stdout.write(self.style.SUCCESS(f"Contactos duplicados consolidados: {merged}."))
