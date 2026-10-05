from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea los roles iniciales de administrador y empleado."

    def handle(self, *args, **options):
        permissions = Permission.objects.filter(content_type__app_label__in=["patients", "grooming", "inventory", "sales", "lost_pets"])
        admin, _ = Group.objects.get_or_create(name="Administrador")
        admin.permissions.set(permissions)
        employee, _ = Group.objects.get_or_create(name="Empleado")
        employee.permissions.set(permissions.filter(codename__in=["view_patient", "view_contact", "view_patientcontact", "view_clinicalrecord", "view_groomingappointment", "view_product", "view_brand", "view_supplier", "view_sale", "add_sale", "view_lostpetreport", "add_lostpetreport", "add_sighting"]))
        self.stdout.write(self.style.SUCCESS("Roles Administrador y Empleado preparados."))
