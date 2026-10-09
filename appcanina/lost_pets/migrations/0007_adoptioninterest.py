from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0006_alter_adoptionpost_species")]
    operations = [
        migrations.CreateModel(
            name="AdoptionInterest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.TextField(max_length=700, verbose_name="mensaje")),
                ("status", models.CharField(choices=[("received", "Recibido"), ("contact", "En conversación"), ("interview", "En evaluación"), ("completed", "Adopción concretada"), ("closed", "No continuó")], default="received", max_length=16, verbose_name="estado")),
                ("staff_note", models.CharField(blank=True, max_length=280, verbose_name="nota visible para la persona")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("applicant", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="adoption_interests", to=settings.AUTH_USER_MODEL, verbose_name="persona interesada")),
                ("post", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interests", to="lost_pets.adoptionpost", verbose_name="publicación")),
            ],
            options={"verbose_name": "interés de adopción", "verbose_name_plural": "intereses de adopción", "ordering": ["-updated_at", "-id"]},
        ),
        migrations.AddConstraint(model_name="adoptioninterest", constraint=models.UniqueConstraint(fields=("post", "applicant"), name="unique_adoption_interest_per_person")),
    ]
