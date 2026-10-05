from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("pacientes/", views.patient_list, name="patient_list"),
    path("buscar/", views.global_search, name="global_search"),
    path("pacientes/nuevo/", views.patient_create, name="patient_create"),
    path("pacientes/<int:patient_id>/contactos/nuevo/", views.patient_contact_create, name="patient_contact_create"),
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
