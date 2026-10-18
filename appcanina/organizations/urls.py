from django.urls import path

from . import views

urlpatterns = [
    path("configuracion-inicial/", views.initial_setup, name="initial_setup"),
    path("comunidad/colaboradores/", views.community_collaborators, name="community_collaborators"),
    path("refugios/", views.shelter_list, name="shelter_list"),
    path("refugios/nuevo/", views.shelter_create, name="shelter_create"),
    path("refugios/<int:shelter_id>/", views.shelter_detail, name="shelter_detail"),
]
