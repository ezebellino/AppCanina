from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("mis-animales/", views.my_animals, name="my_animals"),
    path("mis-animales/<int:patient_id>/", views.my_animal_history, name="my_animal_history"),
    path("mis-animales/<int:patient_id>/compartir/", views.my_animal_sharing, name="my_animal_sharing"),
    path("mis-animales/<int:patient_id>/credencial.pdf", views.my_animal_credential, name="my_animal_credential"),
    path("acceso-viaje/", views.travel_access_request, name="travel_access_request"),
    path("acceso-viaje/<int:request_id>/", views.travel_access_history, name="travel_access_history"),
    path("pacientes/", views.patient_list, name="patient_list"),
    path("atencion/", views.daily_animal_care, name="daily_animal_care"),
    path("buscar/", views.global_search, name="global_search"),
    path("pacientes/nuevo/", views.patient_create, name="patient_create"),
    path("pacientes/<int:patient_id>/contactos/nuevo/", views.patient_contact_create, name="patient_contact_create"),
    path("pacientes/<int:patient_id>/vincular-cuenta/", views.patient_owner_account_link, name="patient_owner_account_link"),
    path("pacientes/<int:patient_id>/contactos/<int:relation_id>/editar/", views.patient_contact_edit, name="patient_contact_edit"),
    path("pacientes/<int:patient_id>/contactos/<int:relation_id>/quitar/", views.patient_contact_remove, name="patient_contact_remove"),
    path("pacientes/<int:patient_id>/historial/nuevo/", views.clinical_record_create, name="clinical_record_create"),
    path("recordatorios/", views.care_reminder_list, name="care_reminder_list"),
    path("pacientes/<int:patient_id>/recordatorios/nuevo/", views.care_reminder_create, name="care_reminder_create"),
    path("recordatorios/<int:reminder_id>/realizar/", views.care_reminder_complete, name="care_reminder_complete"),
    path("pacientes/<int:patient_id>/archivar/", views.patient_archive, name="patient_archive"),
    path("pacientes/<int:patient_id>/", views.patient_detail, name="patient_detail"),
    path("pacientes/<int:patient_id>/editar/", views.patient_edit, name="patient_edit"),
]
