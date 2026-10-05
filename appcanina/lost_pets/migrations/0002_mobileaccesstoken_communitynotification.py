import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="MobileAccessToken", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("label", models.CharField(default="Dispositivo móvil", max_length=80)), ("digest", models.CharField(max_length=64, unique=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("last_used_at", models.DateTimeField(blank=True, null=True)), ("revoked_at", models.DateTimeField(blank=True, null=True)), ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mobile_access_tokens", to=settings.AUTH_USER_MODEL))]),
        migrations.CreateModel(name="CommunityNotification", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("title", models.CharField(max_length=140)), ("body", models.CharField(max_length=280)), ("read_at", models.DateTimeField(blank=True, null=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="community_notifications", to=settings.AUTH_USER_MODEL)), ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="lost_pets.lostpetreport")), ("sighting", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="lost_pets.sighting"))], options={"ordering": ["-created_at"]}),
    ]
