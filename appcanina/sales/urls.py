from django.urls import path
from . import views

urlpatterns = [path("", views.sale_create, name="sale_create"), path("consulta/<int:patient_id>/", views.consultation_charge, name="consultation_charge"), path("desde-turno/<int:appointment_id>/", views.sale_create_from_appointment, name="sale_create_from_appointment"), path("historial/", views.sale_list, name="sale_list"), path("resumen/", views.daily_report, name="daily_report"), path("caja/", views.cash_dashboard, name="cash_dashboard")]
