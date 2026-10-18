from django.db import migrations, models


def assign_existing_posts_to_business(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    AdoptionPost = apps.get_model("lost_pets", "AdoptionPost")
    business = Organization.objects.filter(is_business_profile=True).first()
    if business:
        AdoptionPost.objects.filter(organization__isnull=True).update(organization=business)


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0003_organization_donations_organizationmembership"),
        ("lost_pets", "0008_communitydevicepermission"),
    ]

    operations = [
        migrations.AddField(
            model_name="adoptionpost",
            name="organization",
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.PROTECT, related_name="adoption_posts", to="organizations.organization", verbose_name="organización responsable"),
        ),
        migrations.RunPython(assign_existing_posts_to_business, migrations.RunPython.noop),
    ]
