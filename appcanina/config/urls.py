from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.urls import reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuenta/ingresar/", auth_views.LoginView.as_view(), name="login"),
    path("cuenta/salir/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "cuenta/recuperar/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path("cuenta/recuperar/enviado/", auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("cuenta/restablecer/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html", success_url=reverse_lazy("password_reset_complete")), name="password_reset_confirm"),
    path("cuenta/restablecer/listo/", auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"), name="password_reset_complete"),
    path("", include("organizations.urls")),
    path("", include("patients.urls")),
    path("peluqueria/", include("grooming.urls")),
    path("inventario/", include("inventory.urls")),
    path("ventas/", include("sales.urls")),
    path("visitas/", include("visits.urls")),
    path("extraviados/", include("lost_pets.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
