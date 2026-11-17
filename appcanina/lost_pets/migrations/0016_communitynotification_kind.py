from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0015_adoptionarchive")]
    operations = [
        migrations.AddField(
            model_name="communitynotification", name="kind",
            field=models.CharField(max_length=24, blank=True, default=""),
        ),
    ]
