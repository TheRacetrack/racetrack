# Generated by Django 3.2.16 on 2023-03-01 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0028_auto_20230215_1559'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='replica_internal_names',
            field=models.TextField(blank=True, null=True),
        ),
    ]