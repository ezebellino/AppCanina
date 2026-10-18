from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from organizations.models import Organization, OrganizationMembership
from organizations.roles import ensure_base_roles
from patients.models import ClinicalRecord, Contact, OwnerAccountLink, Patient, PatientContact
from lost_pets.models import AdoptionInterest, AdoptionPost, LostPetReport


DEMO_PASSWORD = "DemoAppCanina2026!"
DEMO_PREFIX = "[DEMO]"


class Command(BaseCommand):
    help = "Carga o elimina una demostración ficticia de Veterinaria, Refugio y Usuario."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Elimina únicamente los datos identificados como DEMO.")

    def _user(self, username, first_name, email):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={"first_name": first_name, "email": email},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])
        return user, created

    def _clear(self):
        demo_organizations = Organization.objects.filter(name__startswith=DEMO_PREFIX)
        AdoptionPost.objects.filter(organization__in=demo_organizations).delete()
        LostPetReport.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Patient.objects.filter(microchip__startswith="DEMO-COM-").delete()
        demo_organizations.delete()
        get_user_model().objects.filter(username__in=["demo_veterinaria", "demo_refugio", "demo_usuario"]).delete()
        self.stdout.write(self.style.SUCCESS("Datos DEMO de comunidad eliminados."))

    def handle(self, *args, **options):
        if options["clear"]:
            with transaction.atomic():
                self._clear()
            return

        roles = ensure_base_roles()
        with transaction.atomic():
            veterinarian, vet_created = self._user("demo_veterinaria", "Valentina", "veterinaria.demo@appcanina.local")
            veterinarian.groups.add(roles["admin"])
            refuge_manager, refuge_created = self._user("demo_refugio", "Martín", "refugio.demo@appcanina.local")
            community_user, user_created = self._user("demo_usuario", "Camila", "usuario.demo@appcanina.local")
            refuge_manager.groups.add(roles["collaborator"])
            community_user.groups.add(roles["collaborator"])

            veterinary, _ = Organization.objects.get_or_create(
                name=f"{DEMO_PREFIX} Veterinaria Horizonte",
                defaults={
                    "kind": Organization.Kind.VETERINARY,
                    "is_verified": True,
                    "locality": "Avellaneda",
                    "phone": "11 4000 0001",
                    "email": "veterinaria.demo@appcanina.local",
                    "address": "Avenida Central 100",
                },
            )
            refuge, _ = Organization.objects.get_or_create(
                name=f"{DEMO_PREFIX} Refugio Patitas",
                defaults={
                    "kind": Organization.Kind.SHELTER,
                    "is_verified": True,
                    "locality": "Avellaneda",
                    "phone": "11 4000 0002",
                    "email": "refugio.demo@appcanina.local",
                    "address": "Calle de los Amigos 200",
                    "donation_alias": "refugio.demo.patitas",
                    "donation_message": "Este es un perfil de demostración. Cada colaboración real ayuda a cuidar más animales.",
                },
            )
            OrganizationMembership.objects.get_or_create(organization=veterinary, user=veterinarian, defaults={"role": OrganizationMembership.Role.MANAGER})
            OrganizationMembership.objects.get_or_create(organization=refuge, user=refuge_manager, defaults={"role": OrganizationMembership.Role.MANAGER})
            refuge_permissions = Permission.objects.filter(
                content_type__app_label="lost_pets",
                codename__in=["view_adoptionpost", "change_adoptionpost", "view_adoptioninterest", "change_adoptioninterest"],
            )
            refuge_manager.user_permissions.add(*refuge_permissions)

            contact, _ = Contact.objects.get_or_create(
                email="usuario.demo@appcanina.local",
                defaults={"full_name": "Camila Usuario DEMO", "phone": "11 4000 0003"},
            )
            OwnerAccountLink.objects.get_or_create(contact=contact, user=community_user)
            patient, _ = Patient.objects.get_or_create(
                microchip="DEMO-COM-001",
                defaults={"name": "Canela", "species": Patient.Species.DOG, "breed": "Mestiza", "notes": "Paciente ficticio de demostración."},
            )
            PatientContact.objects.get_or_create(patient=patient, contact=contact, role=PatientContact.Role.RESPONSIBLE, defaults={"is_primary": True})
            ClinicalRecord.objects.get_or_create(
                patient=patient,
                professional=veterinarian,
                reason="Control preventivo DEMO",
                defaults={"notes": "Ficha ficticia para demostrar historial compartido."},
            )

            animals = [
                ("Mora", "dog", "Mestiza", "2 años", "Juguetona y sociable; ideal para una familia con patio.", AdoptionPost.Status.PUBLISHED),
                ("Nilo", "cat", "Atigrado", "1 año", "Curioso, tranquilo y acostumbrado a vivir en interior.", AdoptionPost.Status.PUBLISHED),
                ("Luna", "dog", "Cruza labrador", "4 años", "Compañera dulce, vacunada y lista para conocer una familia.", AdoptionPost.Status.PUBLISHED),
                ("Pipa", "cat", "Carey", "8 meses", "Pequeña exploradora que busca un hogar responsable.", AdoptionPost.Status.PUBLISHED),
                ("Rocco", "dog", "Mestizo", "3 años", "Energético y muy compañero para paseos diarios.", AdoptionPost.Status.PUBLISHED),
                ("Olivia", "cat", "Blanco y negro", "2 años", "Cariñosa y paciente; convive bien con otros gatos.", AdoptionPost.Status.PUBLISHED),
                ("Bongo", "other", "Conejo", "1 año", "Conejo manso; requiere un espacio seguro y cuidado informado.", AdoptionPost.Status.PUBLISHED),
                ("Simba", "dog", "Mestizo", "5 años", "Adopción concretada: mantiene su ficha como caso de éxito.", AdoptionPost.Status.ADOPTED),
                ("Mía", "cat", "Siamesa", "3 años", "En evaluación de una familia interesada.", AdoptionPost.Status.PENDING),
            ]
            posts = {}
            for name, species, breed, age, description, status in animals:
                post, _ = AdoptionPost.objects.get_or_create(
                    organization=refuge,
                    publisher=refuge_manager,
                    name=name,
                    defaults={
                        "species": species,
                        "breed": breed,
                        "age_label": age,
                        "description": f"{DEMO_PREFIX} {description}",
                        "area_label": "Avellaneda",
                        "status": status,
                    },
                )
                posts[name] = post
            AdoptionInterest.objects.get_or_create(
                post=posts["Mora"],
                applicant=community_user,
                defaults={
                    "message": "[DEMO] Me gustaría conocer a Mora. Tengo experiencia y tiempo para acompañarla.",
                    "status": AdoptionInterest.Status.INTERVIEW,
                    "staff_note": "[DEMO] Entrevista coordinada para el sábado.",
                },
            )
            report, _ = LostPetReport.objects.get_or_create(
                reporter=community_user,
                name=f"{DEMO_PREFIX} Tizón",
                defaults={
                    "species": "cat",
                    "breed": "Negro",
                    "description": "Aviso ficticio para demostrar colaboración comunitaria.",
                    "last_seen_at": timezone.now(),
                    "area_label": "Avellaneda",
                    "status": LostPetReport.Status.PUBLISHED,
                    "latitude": "-34.661100",
                    "longitude": "-58.365300",
                },
            )
            # Older DEMO loads predate the map. Add only its deliberately
            # approximate source point; public output remains rounded/jittered.
            if report.latitude is None or report.longitude is None:
                report.latitude = "-34.661100"
                report.longitude = "-58.365300"
                report.save(update_fields=["latitude", "longitude"])

        created = [label for label, value in [("Veterinaria", vet_created), ("Refugio", refuge_created), ("Usuario", user_created)] if value]
        self.stdout.write(self.style.SUCCESS("Demo de Comunidad lista" + (f" (cuentas nuevas: {', '.join(created)})" if created else "") + "."))
        self.stdout.write("Credenciales DEMO: demo_veterinaria, demo_refugio y demo_usuario · contraseña: DemoAppCanina2026!")
