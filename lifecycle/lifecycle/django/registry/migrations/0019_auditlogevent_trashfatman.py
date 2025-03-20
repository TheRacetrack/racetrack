# Generated by Django 3.2.6 on 2022-04-06 13:00

from django.db import migrations, models
import lifecycle.django.registry.models
import racetrack_client.utils.time


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0018_fatman_last_call_time'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLogEvent',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('version', models.IntegerField(default=1)),
                ('timestamp', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('event_type', models.CharField(max_length=512)),
                ('properties', models.TextField(null=True)),
                ('username_executor', models.CharField(max_length=512, null=True)),
                ('username_subject', models.CharField(max_length=512, null=True)),
                ('fatman_name', models.CharField(max_length=512, null=True)),
                ('fatman_version', models.CharField(max_length=256, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TrashFatman',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=512)),
                ('version', models.CharField(max_length=256)),
                ('status', models.CharField(choices=[('created', 'created'), ('running', 'running'), ('error', 'error'), ('orphaned', 'orphaned'), ('lost', 'lost')], max_length=32)),
                ('create_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('update_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('delete_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('manifest', models.TextField(blank=True, null=True)),
                ('internal_name', models.CharField(blank=True, max_length=512, null=True)),
                ('error', models.TextField(blank=True, null=True)),
                ('image_tag', models.CharField(max_length=256, null=True)),
                ('deployed_by', models.CharField(max_length=256, null=True)),
                ('last_call_time', models.DateTimeField(blank=True, null=True)),
                ('age_days', models.DecimalField(decimal_places=3, max_digits=6)),
            ],
            options={
                'verbose_name_plural': 'Trash Fatmen',
            },
        ),
    ]
