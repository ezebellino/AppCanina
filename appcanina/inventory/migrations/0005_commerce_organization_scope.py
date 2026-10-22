from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_inventory_to_primary_business(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Supplier = apps.get_model("inventory", "Supplier")
    Brand = apps.get_model("inventory", "Brand")
    Product = apps.get_model("inventory", "Product")
    primary = Organization.objects.filter(is_business_profile=True).order_by("id").first()
    if not primary:
        return
    Supplier.objects.filter(organization__isnull=True).update(organization=primary)
    Brand.objects.filter(organization__isnull=True).update(organization=primary)
    Product.objects.filter(organization__isnull=True).update(organization=primary)


class Migration(migrations.Migration):
    dependencies = [("inventory", "0004_product_commercial_name"), ("organizations", "0005_organization_verification")]

    operations = [
        migrations.AddField(model_name="supplier", name="organization", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="suppliers", to="organizations.organization")),
        migrations.AddField(model_name="brand", name="organization", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="brands", to="organizations.organization")),
        migrations.AddField(model_name="product", name="organization", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="products", to="organizations.organization")),
        migrations.AlterField(model_name="supplier", name="name", field=models.CharField(max_length=140, verbose_name="nombre")),
        migrations.AlterField(model_name="brand", name="name", field=models.CharField(max_length=100, verbose_name="nombre")),
        migrations.AlterField(model_name="product", name="sku", field=models.CharField(blank=True, max_length=50, null=True, verbose_name="código interno")),
        migrations.RunPython(assign_legacy_inventory_to_primary_business, migrations.RunPython.noop),
        migrations.AddConstraint(model_name="supplier", constraint=models.UniqueConstraint(fields=("organization", "name"), name="unique_supplier_per_organization")),
        migrations.AddConstraint(model_name="brand", constraint=models.UniqueConstraint(fields=("organization", "name"), name="unique_brand_per_organization")),
        migrations.AddConstraint(model_name="product", constraint=models.UniqueConstraint(fields=("organization", "sku"), name="unique_product_sku_per_organization")),
    ]
