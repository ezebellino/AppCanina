from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('lost_pets', '0016_communitynotification_kind')]
    operations = [
        migrations.AddField(model_name='adoptionpost', name='locality', field=models.CharField('localidad del animal', max_length=120, blank=True)),
        migrations.AddField(model_name='adoptionpost', name='location_latitude', field=models.DecimalField('latitud aproximada', max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('-90')), MaxValueValidator(Decimal('90'))])),
        migrations.AddField(model_name='adoptionpost', name='location_longitude', field=models.DecimalField('longitud aproximada', max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal('-180')), MaxValueValidator(Decimal('180'))])),
    ]
