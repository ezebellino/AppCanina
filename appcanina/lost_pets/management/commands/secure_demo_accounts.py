import hashlib
import sys
import warnings
from getpass import GetPassWarning, getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from lost_pets.models import MobileAccessToken, MobilePushDevice


DEMO_USERS = ("demo_veterinaria", "demo_refugio", "demo_usuario", "demo_veterinaria_admin")
# Deny the retired shared credential without retaining it in source or output.
RETIRED_PASSWORD_DIGEST = "eefca9c6d53f03d97dfd87dfb3e32ec7855cb1536ecf18f8e5f121dcdf7381a3"


class Command(BaseCommand):
    help = "Revisa los accesos DEMO; --apply rota claves de forma interactiva sin borrar datos."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Pide claves privadas y aplica la rotación.")
        parser.add_argument("--admin", help="Administrador real que ya pudo iniciar sesión.")

    def _admin(self, username):
        User = get_user_model()
        if not username or username.lower().startswith("demo_"):
            raise CommandError("Indicá --admin con tu administrador real, fuera de los DEMO.")
        user = User.objects.filter(username=username, is_active=True, is_staff=True, last_login__isnull=False).first()
        if not user or not user.has_usable_password():
            raise CommandError("No se verificó un administrador activo con acceso previo. No se modificó nada.")
        return user

    def handle(self, *args, **options):
        User = get_user_model()
        users = list(User.objects.filter(username__in=DEMO_USERS).order_by("username"))
        for user in users:
            self.stdout.write(f"{user.username}: activo={user.is_active}, staff={user.is_staff}, superusuario={user.is_superuser}")
        if not options["apply"]:
            self.stdout.write("Solo revisión. No se modificaron cuentas, claves ni datos.")
            return
        admin = self._admin(options["admin"])
        if not users:
            self.stdout.write("No hay cuentas DEMO conocidas para proteger.")
            return
        if not sys.stdin.isatty():
            raise CommandError("Usá una terminal SSH interactiva: no se aceptan claves por argumentos ni entrada redirigida.")
        prepared = {}
        seen = {RETIRED_PASSWORD_DIGEST}
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", GetPassWarning)
                for user in users:
                    password = getpass(f"Nueva clave privada para {user.username}: ")
                    confirmation = getpass("Repetir clave: ")
                    if password != confirmation:
                        raise CommandError("Las claves no coinciden. No se modificó ninguna cuenta.")
                    validate_password(password, user)
                    digest = hashlib.sha256(password.encode()).hexdigest()
                    if digest in seen or user.check_password(password) or admin.check_password(password):
                        raise CommandError("Usá una clave nueva y distinta por cuenta, diferente de la retirada y de tu administrador. No se modificó nada.")
                    seen.add(digest)
                    prepared[user.pk] = make_password(password)
                    del password, confirmation
        except ValidationError as error:
            raise CommandError("No se modificó ninguna cuenta. " + " ".join(error.messages))
        except (EOFError, KeyboardInterrupt, GetPassWarning):
            raise CommandError("Entrada cancelada o terminal sin ocultación segura. No se modificó ninguna cuenta.")

        # No write transaction is held while the operator types passwords.
        with transaction.atomic():
            self._admin(options["admin"])
            current = list(User.objects.select_for_update().filter(username__in=DEMO_USERS).order_by("username"))
            snapshot = lambda rows: [(u.pk, u.username, u.password, u.is_active, u.is_staff, u.is_superuser) for u in rows]
            if snapshot(current) != snapshot(users):
                raise CommandError("Las cuentas cambiaron durante la preparación. Repetí la operación; no se modificó nada.")
            for user in current:
                user.password = prepared[user.pk]
                user.is_staff = False
                user.is_superuser = False
                user.save(update_fields=["password", "is_staff", "is_superuser"])
            ids = [user.pk for user in current]
            MobileAccessToken.objects.filter(user_id__in=ids, revoked_at__isnull=True).update(revoked_at=timezone.now())
            MobilePushDevice.objects.filter(user_id__in=ids).update(active=False)
        # Django rejects old browser sessions through the changed auth hash.
        self.stdout.write(self.style.SUCCESS(f"Protegidas {len(users)} cuentas DEMO. Claves renovadas; sesiones anteriores invalidadas; sin permisos de plataforma. Datos y roles institucionales conservados."))
