# Generated by Django 3.2.3 on 2021-07-26 18:57

from django.db import migrations, models
import lifecycle.django.registry.models
import racetrack_client.utils.time


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Deployment',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('in_progress', 'in_progress'), ('done', 'done'), ('failed', 'failed')], max_length=32)),
                ('create_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('update_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('manifest', models.TextField()),
                ('job_name', models.CharField(max_length=512)),
                ('error', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Job',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=512, unique=True)),
                ('status', models.CharField(choices=[('created', 'created'), ('running', 'running'), ('orphaned', 'orphaned'), ('lost', 'lost')], max_length=32)),
                ('create_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('update_time', models.DateTimeField(default=racetrack_client.utils.time.now)),
                ('manifest', models.TextField(blank=True, null=True)),
                ('internal_name', models.CharField(blank=True, max_length=512, null=True)),
                ('error', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Esc',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=512)),
                ('jobs', models.ManyToManyField(blank=True, related_name='escs', to='registry.Job')),
            ],
        ),
    ]
