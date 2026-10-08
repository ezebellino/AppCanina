from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("lost_pets", "0003_mobilepushdevice"),
    ]

    operations = [
        migrations.AddField(
            model_name="lostpetreport",
            name="requested_via_mobile",
            field=models.BooleanField(default=False, verbose_name="solicitud enviada desde la comunidad"),
        ),
        migrations.AddField(
            model_name="lostpetreport",
            name="review_note",
            field=models.CharField(blank=True, max_length=280, verbose_name="nota para la solicitud"),
        ),
        migrations.AlterField(
            model_name="lostpetreport",
            name="status",
            field=models.CharField(choices=[("published", "Publicado"), ("hidden", "Oculto"), ("rejected", "Rechazado"), ("resolved", "Resuelto"), ("archived", "Archivado")], default="published", max_length=16, verbose_name="estado"),
        ),
    ]
