# Generated manually to remove the unused 'validado' field from Participacion model

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('formacion', '0018_alter_puestodetrabajo_nombre'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participacion',
            name='validado',
        ),
    ]