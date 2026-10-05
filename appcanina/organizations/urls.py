from django.urls import path

from . import views

urlpatterns = [
    path("configuracion-inicial/", views.initial_setup, name="initial_setup"),
    path("comunidad/colaboradores/", views.community_collaborators, name="community_collaborators"),
]
