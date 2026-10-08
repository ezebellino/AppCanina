from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0004_lostpetreport_mobile_request_review")]
    operations = [
        migrations.CreateModel(
            name="AdoptionPost",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, verbose_name="nombre del animal")),
                ("species", models.CharField(choices=[("dog", "Perro"), ("cat", "Gato"), ("other", "Otro")], max_length=12, verbose_name="especie")),
                ("breed", models.CharField(blank=True, max_length=100, verbose_name="raza")),
                ("age_label", models.CharField(blank=True, max_length=80, verbose_name="edad aproximada")),
                ("description", models.TextField(blank=True, verbose_name="descripción")),
                ("photo", models.ImageField(blank=True, upload_to="adoptions/%Y/%m/", verbose_name="foto")),
                ("area_label", models.CharField(max_length=120, verbose_name="zona o barrio")),
                ("status", models.CharField(choices=[("pending", "En revisión"), ("published", "Publicado"), ("rejected", "Rechazado"), ("adopted", "Adoptado"), ("archived", "Archivado")], default="pending", max_length=16, verbose_name="estado")),
                ("review_note", models.CharField(blank=True, max_length=280, verbose_name="nota para quien publicó")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("publisher", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="adoption_posts", to=settings.AUTH_USER_MODEL, verbose_name="publicado por")),
            ],
            options={"verbose_name": "publicación de adopción", "verbose_name_plural": "publicaciones de adopción", "ordering": ["status", "-created_at", "-id"]},
        ),
    ]
