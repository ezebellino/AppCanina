from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0004_organization_locality")]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="is_verified",
            field=models.BooleanField(default=True, verbose_name="perfil institucional verificado"),
        ),
        migrations.AlterField(
            model_name="organization",
            name="is_verified",
            field=models.BooleanField(default=False, verbose_name="perfil institucional verificado"),
        ),
    ]
