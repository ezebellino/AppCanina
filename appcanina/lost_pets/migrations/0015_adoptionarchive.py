from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("lost_pets", "0014_pushworkerlease_pushdelivery"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.CreateModel(
        name="AdoptionArchive",
        fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("audience", models.CharField(choices=[("applicant", "Solicitante"), ("institution", "Institución")], max_length=16)),
            ("version", models.DateTimeField()),
            ("interest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="archives", to="lost_pets.adoptioninterest")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
        ],
        options={"constraints": [models.UniqueConstraint(fields=("interest", "user", "audience"), name="unique_adoption_archive")]},
    )]
