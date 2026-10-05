from django.core.management.base import BaseCommand

from organizations.roles import ensure_base_roles


class Command(BaseCommand):
    help = "Crea los roles Administrador, Empleado y Colaborador comunitario."

    def handle(self, *args, **options):
        ensure_base_roles()
        self.stdout.write(self.style.SUCCESS("Roles Administrador, Empleado y Colaborador comunitario preparados."))
