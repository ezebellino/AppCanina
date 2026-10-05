# Generated manually for the optional professional product label.
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("inventory", "0003_product_batch_product_expires_on_and_more")]

    operations = [
        migrations.AddField(
            model_name="product",
            name="commercial_name",
            field=models.CharField(blank=True, max_length=220, verbose_name="nombre comercial o profesional"),
        ),
    ]
