from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("lost_pets", "0005_adoptionpost")]
    operations = [
        migrations.AlterField(
            model_name="adoptionpost",
            name="species",
            field=models.CharField(choices=[("dog", "Perro"), ("cat", "Gato"), ("other", "Otra")], max_length=12, verbose_name="especie"),
        ),
    ]
