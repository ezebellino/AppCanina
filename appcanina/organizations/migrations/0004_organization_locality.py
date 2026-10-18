from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("organizations", "0003_organization_donations_organizationmembership")]
    operations = [migrations.AddField(model_name="organization", name="locality", field=models.CharField(blank=True, max_length=120, verbose_name="localidad"))]
