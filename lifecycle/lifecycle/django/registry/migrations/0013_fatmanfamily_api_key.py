# Generated by Django 3.2.6 on 2021-10-25 12:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0012_deployment_build_logs'),
    ]

    operations = [
        migrations.AddField(
            model_name='fatmanfamily',
            name='api_key',
            field=models.CharField(blank=True, max_length=36, null=True),
        ),
    ]