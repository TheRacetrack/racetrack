# Generated by Django 4.2.7 on 2024-06-14 06:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0036_job_infrastructure_stats"),
    ]

    operations = [
        migrations.AddField(
            model_name="deployment",
            name="warnings",
            field=models.TextField(blank=True, null=True),
        ),
    ]