from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("lost_pets", "0002_mobileaccesstoken_communitynotification"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MobilePushDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=255, unique=True)),
                ("platform", models.CharField(choices=[("android", "Android"), ("ios", "iOS")], max_length=12)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobile_push_devices", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "dispositivo con notificaciones", "verbose_name_plural": "dispositivos con notificaciones"},
        ),
    ]
