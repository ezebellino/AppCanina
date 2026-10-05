from django.urls import path

from . import views
from . import api


urlpatterns = [
    path("", views.report_list, name="lost_pet_list"),
    path("mapa/", views.map_view, name="lost_pet_map"),
    path("api/v1/mapa/", views.map_data, name="lost_pet_map_data"),
    path("api/v1/sesion/", api.mobile_login, name="mobile_login"),
    path("api/v1/notificaciones/", api.mobile_notifications, name="mobile_notifications"),
    path("nuevo/", views.report_create, name="lost_pet_create"),
    path("<int:report_id>/", views.report_detail, name="lost_pet_detail"),
    path("<int:report_id>/avistamientos/nuevo/", views.sighting_create, name="sighting_create"),
    path("<int:report_id>/estado/", views.report_change_status, name="lost_pet_change_status"),
]
