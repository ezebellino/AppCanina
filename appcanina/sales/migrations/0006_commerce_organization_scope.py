from django.db import migrations, models
import django.db.models.deletion


def assign_legacy_commerce_to_primary_business(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Sale = apps.get_model("sales", "Sale")
    CashSession = apps.get_model("sales", "CashSession")
    primary = Organization.objects.filter(is_business_profile=True).order_by("id").first()
    for sale in Sale.objects.filter(organization__isnull=True).select_related("product", "patient"):
        organization_id = (sale.product.organization_id if sale.product_id else None) or (sale.patient.organization_id if sale.patient_id else None) or (primary.id if primary else None)
        if organization_id:
            Sale.objects.filter(pk=sale.pk).update(organization_id=organization_id)
    for session in CashSession.objects.filter(organization__isnull=True):
        sale = Sale.objects.filter(cash_session_id=session.pk, organization__isnull=False).order_by("id").first()
        organization_id = sale.organization_id if sale else (primary.id if primary else None)
        if organization_id:
            CashSession.objects.filter(pk=session.pk).update(organization_id=organization_id)


class Migration(migrations.Migration):
    dependencies = [("sales", "0005_sale_contact"), ("inventory", "0005_commerce_organization_scope"), ("organizations", "0005_organization_verification")]

    operations = [
        migrations.AddField(model_name="sale", name="organization", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="sales", to="organizations.organization")),
        migrations.AddField(model_name="cashsession", name="organization", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cash_sessions", to="organizations.organization")),
        migrations.RunPython(assign_legacy_commerce_to_primary_business, migrations.RunPython.noop),
    ]
