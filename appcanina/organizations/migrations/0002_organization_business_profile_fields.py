# Generated manually for the business identity profile.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="address",
            field=models.CharField(blank=True, max_length=220, verbose_name="dirección"),
        ),
        migrations.AddField(
            model_name="organization",
            name="email",
            field=models.EmailField(blank=True, max_length=254, verbose_name="correo electrónico"),
        ),
        migrations.AddField(
            model_name="organization",
            name="is_business_profile",
            field=models.BooleanField(default=False, verbose_name="es el perfil del negocio"),
        ),
        migrations.AddField(
            model_name="organization",
            name="logo",
            field=models.ImageField(blank=True, upload_to="organizations/logos/", verbose_name="logo"),
        ),
        migrations.AddField(
            model_name="organization",
            name="phone",
            field=models.CharField(blank=True, max_length=40, verbose_name="teléfono"),
        ),
    ]
