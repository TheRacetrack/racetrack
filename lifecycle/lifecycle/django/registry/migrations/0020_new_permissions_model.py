# Generated by Django 3.2.6 on 2022-05-04 12:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import lifecycle.django.registry.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('registry', '0019_auditlogevent_trashfatman'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuthResourcePermission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scope', models.CharField(choices=[('read_fatman', 'read_fatman'), ('deploy_fatman', 'deploy_fatman'), ('deploy_new_family', 'deploy_new_family'), ('delete_fatman', 'delete_fatman'), ('call_fatman', 'call_fatman'), ('call_admin_api', 'call_admin_api'), ('full_access', 'full_access')], max_length=32)),
                ('all_resources', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='AuthSubject',
            fields=[
                ('id', models.CharField(default=lifecycle.django.registry.models.new_uuid, max_length=36, primary_key=True, serialize=False)),
                ('token', models.CharField(max_length=1024)),
                ('expiry_time', models.DateTimeField(blank=True, null=True)),
                ('active', models.BooleanField(default=True)),
            ],
        ),
        migrations.AddField(
            model_name='authsubject',
            name='esc',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registry.esc'),
        ),
        migrations.AddField(
            model_name='authsubject',
            name='fatman_family',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registry.fatmanfamily'),
        ),
        migrations.AddField(
            model_name='authsubject',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='authresourcepermission',
            name='auth_subject',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='registry.authsubject'),
        ),
        migrations.AddField(
            model_name='authresourcepermission',
            name='fatman',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registry.fatman'),
        ),
        migrations.AddField(
            model_name='authresourcepermission',
            name='fatman_family',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='registry.fatmanfamily'),
        ),
    ]
