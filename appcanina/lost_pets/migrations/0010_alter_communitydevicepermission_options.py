from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("lost_pets", "0009_adoptionpost_organization"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="communitydevicepermission",
            options={
                "verbose_name": "permisos de dispositivo comunitario",
                "verbose_name_plural": "permisos de dispositivos comunitarios",
            },
        ),
    ]
