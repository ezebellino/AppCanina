from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_visit_list, name="home_visit_list"),
    path("nueva/", views.home_visit_create, name="home_visit_create"),
    path("<int:visit_id>/editar/", views.home_visit_edit, name="home_visit_edit"),
]
