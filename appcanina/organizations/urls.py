from django.urls import path

from . import views

urlpatterns = [
    path("configuracion-inicial/", views.initial_setup, name="initial_setup"),
    path("plataforma/", views.platform_dashboard, name="platform_dashboard"),
    path("comunidad/colaboradores/", views.community_collaborators, name="community_collaborators"),
    path("organizaciones/validaciones/", views.organization_verification_list, name="organization_verification_list"),
    path("organizaciones/<int:organization_id>/validacion/", views.organization_verification_update, name="organization_verification_update"),
    path("refugios/", views.shelter_list, name="shelter_list"),
    path("refugios/nuevo/", views.shelter_create, name="shelter_create"),
    path("refugios/<int:shelter_id>/", views.shelter_detail, name="shelter_detail"),
]
