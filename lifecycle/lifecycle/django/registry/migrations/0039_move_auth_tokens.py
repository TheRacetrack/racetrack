from django.db import migrations


def move_tokens_to_auth_token_models(apps, schema_editor):
    AuthSubject = apps.get_model('registry', 'AuthSubject')
    AuthToken = apps.get_model('registry', 'AuthToken')
    for auth_subject in AuthSubject.objects.all():
        auth_token = AuthToken()
        auth_token.auth_subject = auth_subject
        auth_token.token = auth_subject.token
        auth_token.expiry_time = auth_subject.expiry_time
        auth_token.active = auth_subject.active
        auth_token.save()


class Migration(migrations.Migration):

    dependencies = [
        ("registry", "0038_create_authtoken"),
    ]

    operations = [
        migrations.RunPython(move_tokens_to_auth_token_models),
        migrations.RemoveField(
            model_name="authsubject",
            name="active",
        ),
        migrations.RemoveField(
            model_name="authsubject",
            name="expiry_time",
        ),
        migrations.RemoveField(
            model_name="authsubject",
            name="token",
        ),
    ]
