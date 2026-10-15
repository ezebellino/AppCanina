from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lost_pets", "0007_adoptioninterest"),
    ]

    operations = [
        migrations.CreateModel(
            name="CommunityDevicePermission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("device_key", models.CharField(max_length=120)),
                ("device_name", models.CharField(default="Dispositivo móvil", max_length=80)),
                ("platform", models.CharField(blank=True, max_length=16)),
                ("camera", models.CharField(choices=[("unknown", "Sin definir"), ("granted", "Permitido"), ("denied", "No permitido")], default="unknown", max_length=12)),
                ("location", models.CharField(choices=[("unknown", "Sin definir"), ("granted", "Permitido"), ("denied", "No permitido")], default="unknown", max_length=12)),
                ("notifications", models.CharField(choices=[("unknown", "Sin definir"), ("granted", "Permitido"), ("denied", "No permitido")], default="unknown", max_length=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="community_device_permissions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="communitydevicepermission",
            constraint=models.UniqueConstraint(fields=("user", "device_key"), name="unique_community_device_permission"),
        ),
    ]
