from django.conf import settings
from django.db import migrations, models


def rename_fatman_to_job(apps, schema_editor):
    AuthResourcePermission = apps.get_model('registry', 'AuthResourcePermission')
    AuditLogEvent = apps.get_model('registry', 'AuditLogEvent')

    # AuthResourcePermission: Rename AuthScope values
    for permission in AuthResourcePermission.objects.all():
        if 'fatman' in permission.scope:
            permission.scope = permission.scope.replace('fatman', 'job')
            permission.save()

    # AuditLogEvent: Rename event_type values
    for ale in AuditLogEvent.objects.all():
        if 'fatman' in ale.event_type:
            ale.event_type = ale.event_type.replace('fatman', 'job')
            ale.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('registry', '0026_auto_20221207_1014'),
    ]

    operations = [
        migrations.RunPython(rename_fatman_to_job),

        migrations.AlterField(
            model_name='authresourcepermission',
            name='scope',
            field=models.CharField(choices=[('read_job', 'read_job'), ('deploy_job', 'deploy_job'), ('deploy_new_family', 'deploy_new_family'), ('delete_job', 'delete_job'), ('call_job', 'call_job'), ('call_admin_api', 'call_admin_api'), ('full_access', 'full_access')], max_length=32),
        ),
    ]
