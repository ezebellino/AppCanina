"""Permission-aware navigation for the veterinary workspace."""
from django.urls import reverse


def veterinary_navigation(request):
    groups = [
        ("Atención clínica", "care", ("/pacientes/", "/atenciones-autorizadas/", "/visitas/", "/recordatorios/"), [
            ("Pacientes e historias", "patient_list", "patients.view_patient"),
            ("Atenciones autorizadas", "veterinary_authorized_patients", "patients.view_clinicalrecord"),
            ("Recordatorios clínicos", "care_reminder_list", "patients.view_carereminder"),
            ("Visitas a domicilio", "home_visit_list", "visits.view_homevisit"),
        ]),
        ("Peluquería", "grooming", ("/peluqueria/",), [
            ("Agenda y turnos", "grooming_agenda", "grooming.view_groomingappointment"),
            ("Servicios", "grooming_service_list", "grooming.view_groomingservice"),
        ]),
        ("Comercio", "shop", ("/inventario/", "/ventas/"), [
            ("Inventario", "inventory_list", "inventory.view_product"),
            ("Nueva venta", "sale_create", "sales.add_sale"),
            ("Historial de ventas", "sale_list", "sales.view_sale"),
            ("Caja diaria", "cash_dashboard", "sales.view_cashsession"),
            ("Proveedores", "supplier_list", "inventory.view_supplier"),
            ("Marcas", "brand_list", "inventory.view_brand"),
        ]),
        ("Animales extraviados", "community", ("/extraviados/",), [
            ("Ver búsquedas", "lost_pet_list", "lost_pets.view_lostpetreport"),
            ("Publicar aviso", "lost_pet_create", "lost_pets.view_lostpetreport"),
            ("Ver mapa", "lost_pet_map", "lost_pets.view_lostpetreport"),
        ]),
    ]
    current = request.resolver_match.url_name if request.resolver_match else ""
    result = []
    for label, icon, prefixes, entries in groups:
        links = [{"label": title, "url": reverse(name), "active": current == name}
                 for title, name, permission in entries if request.user.has_perm(permission)]
        if links:
            result.append({"label": label, "icon": icon, "links": links,
                           "open": current != "business_profile" and request.path.startswith(prefixes)})
    return result
