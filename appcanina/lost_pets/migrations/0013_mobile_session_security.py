from django.db import migrations, models
from django.utils import timezone
import lost_pets.models
import django.db.models.deletion


def revoke_legacy_sessions(apps, schema_editor):
    Token = apps.get_model("lost_pets", "MobileAccessToken")
    Token.objects.using(schema_editor.connection.alias).filter(
        revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
    apps.get_model("lost_pets", "MobilePushDevice").objects.using(schema_editor.connection.alias).update(active=False)


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0012_adoptioninterest_applicant_activity_at_and_more")]
    operations = [
        migrations.AddField(model_name="mobileaccesstoken", name="expires_at", field=models.DateTimeField(default=lost_pets.models.mobile_token_expiry)),
        migrations.AddField(model_name="mobileaccesstoken", name="password_fingerprint", field=models.CharField(default="", editable=False, max_length=64)),
        migrations.AddField(model_name="mobilepushdevice", name="access_token", field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="push_devices", to="lost_pets.mobileaccesstoken")),
        migrations.RunPython(revoke_legacy_sessions, migrations.RunPython.noop),
    ]
