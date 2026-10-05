from django.urls import path

from . import views

urlpatterns = [path("configuracion-inicial/", views.initial_setup, name="initial_setup")]
