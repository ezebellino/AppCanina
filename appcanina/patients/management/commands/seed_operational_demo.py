from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from grooming.models import GroomingAppointment, GroomingService
from inventory.models import Brand, Product, Supplier
from patients.models import CareReminder, Contact, Patient, PatientContact
from sales.models import Sale, SaleLine
from visits.models import HomeVisit


class Command(BaseCommand):
    help = "Carga datos operativos de demostración sin modificar registros existentes."

    def handle(self, *args, **options):
        owner = get_user_model().objects.filter(is_superuser=True).first()
        if not owner:
            raise CommandError("Primero creá un superusuario con createsuperuser.")

        suppliers = {}
        for name, frequency in [("Distribuidora Mascotas", "weekly"), ("Nutrición Animal", "twice_weekly"), ("Farmacia Vet", "weekly"), ("Hogar Mascota", "as_needed")]:
            suppliers[name], _ = Supplier.objects.get_or_create(name=name, defaults={"visit_frequency": frequency})
        brands = {name: Brand.objects.get_or_create(name=name)[0] for name in ["Purina", "Royal Canin", "Old Prince", "Bayer", "Zoetis", "Eukanuba", "Kong", "Excellent"]}

        product_groups = [
            ("food", "Purina", "Distribuidora Mascotas", "Bolsa de alimento adulto", "bag", 5),
            ("food", "Old Prince", "Nutrición Animal", "Alimento a granel", "kg", 5),
            ("medicine", "Bayer", "Farmacia Vet", "Antiinflamatorio veterinario", "unit", 5),
            ("antiparasitic", "Zoetis", "Farmacia Vet", "Pipeta antiparasitaria", "unit", 5),
            ("shampoo", "Eukanuba", "Hogar Mascota", "Shampoo para mascotas", "unit", 5),
            ("toy", "Kong", "Hogar Mascota", "Juguete interactivo", "unit", 5),
            ("accessory", "Kong", "Hogar Mascota", "Correa reforzada", "unit", 5),
            ("bed", "Excellent", "Hogar Mascota", "Cama acolchada", "unit", 5),
            ("clothing", "Excellent", "Hogar Mascota", "Abrigo impermeable", "unit", 5),
            ("hygiene", "Eukanuba", "Hogar Mascota", "Toallitas higiénicas", "unit", 5),
        ]
        products = []
        for group_index, (category, brand_name, supplier_name, label, unit, count) in enumerate(product_groups, start=1):
            for item in range(1, count + 1):
                sku = f"DEMO-{group_index:02d}-{item:02d}"
                defaults = {
                    "name": f"{label} {item}", "category": category, "brand": brands[brand_name],
                    "supplier": suppliers[supplier_name], "sale_unit": unit,
                    "price": Decimal(3500 + group_index * 2250 + item * 700),
                    "stock": Decimal(3 if item == 1 else 12 + item), "minimum_stock": Decimal(5),
                    "quality": "Demo operativa",
                }
                if unit == "bag":
                    defaults["package_weight_kg"] = Decimal(item * 3)
                product, _ = Product.objects.get_or_create(sku=sku, defaults=defaults)
                products.append(product)

        names = ["Mora", "Simón", "Lola", "Bruno", "Nina", "Toto", "Kiara", "Rocco", "Luna", "Toby", "Milo", "Frida", "Coco", "Olivia", "Rocky", "Emma", "Bauti", "Pipa", "Dante", "Mía", "Max", "Uma", "Zeus", "Violeta", "Benito", "Kira", "Pancho", "Sasha", "Teo", "Alma", "Boris", "Canela", "Felipe", "Maya", "Simba", "Mila", "Otto", "Renata", "Charly", "Dulce", "Rufina", "Balú", "Tina", "Polo", "Nala", "Paco", "Ayla", "Thor", "Lía", "Rita"]
        patients = []
        for index, name in enumerate(names, start=1):
            patient, _ = Patient.objects.get_or_create(microchip=f"DEMO-CHIP-{index:03d}", defaults={"name": name, "species": "cat" if index % 5 == 0 else "dog", "breed": "Mestizo", "notes": "Ficha creada para demostración operativa."})
            contact, _ = Contact.objects.get_or_create(phone=f"11-5555-{index:04d}", defaults={"full_name": f"Familia demostración {((index - 1) // 2) + 1}", "email": f"demo{index}@appcanina.local"})
            PatientContact.objects.get_or_create(patient=patient, contact=contact, role="responsible", defaults={"is_primary": True})
            patients.append(patient)

        service_specs = [("Baño y secado", 45, 8500), ("Corte higiénico", 30, 6500), ("Corte de uñas", 20, 3500), ("Baño y corte", 75, 13500), ("Cepillado intensivo", 30, 5500)]
        services = []
        for name, duration, price in service_specs:
            service, _ = GroomingService.objects.get_or_create(name=name, defaults={"duration_minutes": duration, "price": Decimal(price)})
            services.append(service)

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        demo_day = timezone.localtime(now).replace(hour=8) + timedelta(days=7)
        for index, patient in enumerate(patients[:18]):
            if GroomingAppointment.objects.filter(patient=patient).exists():
                continue
            starts_at = demo_day + timedelta(hours=index * 2)
            appointment = GroomingAppointment.objects.create(patient=patient, starts_at=starts_at, service=services[index % len(services)], status="confirmed" if index < 8 else "booked", assigned_to=owner, notes=f"Demo operativa #{index + 1}")
            created = True
            if created and index % 4 == 0:
                appointment.additional_services.add(services[(index + 1) % len(services)])
                appointment.update_end_time_from_services()

        for index, patient in enumerate(patients[18:24], start=1):
            scheduled_for = demo_day + timedelta(hours=index * 3)
            HomeVisit.objects.get_or_create(
                patient=patient,
                scheduled_for=scheduled_for,
                defaults={"assigned_to": owner, "visit_type": "clinical" if index % 2 else "delivery", "status": "confirmed" if index < 3 else "requested", "address": f"Calle Demo {100 + index}", "zone": "Centro", "reason": "Atención de demostración", "price": Decimal(9000 + index * 1000)},
            )

        for index, patient in enumerate(patients[:10], start=1):
            CareReminder.objects.get_or_create(patient=patient, kind=("vaccine", "antiparasitic", "clinical_control")[index % 3], due_on=timezone.localdate() + timedelta(days=index - 4), defaults={"notes": "Recordatorio de demostración"})

        for index, product in enumerate(products[:12], start=1):
            if Sale.objects.filter(payment_reference=f"DEMO-VENTA-{index:02d}").exists():
                continue
            quantity = Decimal("0.5") if product.sale_unit == "kg" else Decimal("1")
            total = (product.current_price * quantity).quantize(Decimal("0.01"))
            sale = Sale.objects.create(patient=patients[index - 1], contact=patients[index - 1].contacts.first(), total=total, payment_method=("cash", "transfer", "qr")[index % 3], payment_reference=f"DEMO-VENTA-{index:02d}", seller=owner, created_at=timezone.now() - timedelta(minutes=index * 18))
            SaleLine.objects.create(sale=sale, product=product, description=product.name, quantity=quantity, unit_price=product.current_price, total=total)

        self.stdout.write(self.style.SUCCESS("Demo lista: 50 productos, 50 pacientes, 5 servicios, turnos y ventas de muestra."))
