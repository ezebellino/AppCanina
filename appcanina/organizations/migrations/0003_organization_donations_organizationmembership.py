from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_organization_business_profile_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="donation_alias",
            field=models.CharField(blank=True, max_length=120, verbose_name="alias para colaboraciones"),
        ),
        migrations.AddField(
            model_name="organization",
            name="donation_message",
            field=models.CharField(blank=True, help_text="Se verá debajo de las publicaciones de adopción del refugio.", max_length=220, verbose_name="mensaje de colaboración"),
        ),
        migrations.CreateModel(
            name="OrganizationMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("manager", "Responsable"), ("staff", "Equipo")], default="manager", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="memberships", to="organizations.organization")),
                ("user", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="organization_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "integrante de organización", "verbose_name_plural": "integrantes de organizaciones"},
        ),
        migrations.AddConstraint(
            model_name="organizationmembership",
            constraint=models.UniqueConstraint(fields=("organization", "user"), name="unique_organization_membership"),
        ),
    ]
