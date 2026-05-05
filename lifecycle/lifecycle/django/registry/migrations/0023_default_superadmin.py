import os
from typing import Optional, List
import dataclasses
from dataclasses import dataclass

import jwt
from django.contrib.auth.admin import User
from django.db import migrations
from django.db.models.signals import pre_init, post_init, pre_save, post_save


class DisableSignals:
    def __init__(self):
        self.stashed_signals = {}
        self.disabled_signals = [
            pre_init, post_init,
            pre_save, post_save,
        ]

    def __enter__(self):
        for signal in self.disabled_signals:
            self.disconnect(signal)

    def __exit__(self, exc_type, exc_val, exc_tb):
        for signal in self.stashed_signals.keys():
            self.reconnect(signal)

    def disconnect(self, signal):
        self.stashed_signals[signal] = signal.receivers
        signal.receivers = []

    def reconnect(self, signal):
        signal.receivers = self.stashed_signals.get(signal, [])


def create_default_superuser(apps, schema_editor):
    with DisableSignals():
        try:
            user = User.objects.get(username='admin')
        except User.DoesNotExist:
            user = User()
            user.is_active = True
            user.is_superuser = True
            user.is_staff = True
            user.username = 'admin'
            user.email = 'admin@example.com'
            user.set_password('admin')
            user.save()

        AuthUser = apps.get_model('auth', 'User')
        user = AuthUser.objects.get(username='admin')

        setup_superuser_permissions(apps, user)


def setup_superuser_permissions(apps, user_model):
    AuthSubject = apps.get_model('registry', 'AuthSubject')
    AuthResourcePermission = apps.get_model('registry', 'AuthResourcePermission')

    auth_subject = create_auth_subject_for_superuser(user_model, AuthSubject)
    grant_superuser_permissions(auth_subject, AuthResourcePermission)


def create_auth_subject_for_superuser(user_model, AuthSubject):
    try:
        auth_subject = AuthSubject.objects.get(user=user_model)
    except AuthSubject.DoesNotExist:
        auth_subject = AuthSubject()
        auth_subject.user = user_model
        auth_subject.active = True

    auth_subject.token = generate_auth_token('admin', 'user', 'ce081b05-a4a0-414a-8f6a-84c0231916a6')
    auth_subject.save()
    return auth_subject


def grant_superuser_permissions(
    auth_subject,
    AuthResourcePermission,
):
    permission = AuthResourcePermission(
        auth_subject=auth_subject,
        all_resources=True,
        scope='full_access',
    )
    permission.save()


@dataclass
class AuthTokenPayload:
    # unique token ID used to generate a token
    seed: str
    # whom the token refers to
    subject: str
    # AuthSubjectType value
    subject_type: str
    # AuthScope values
    scopes: Optional[List[str]] = None


def generate_auth_token(
    subject_name: str,
    subject_type_value: str,
    seed: str,
) -> str:
    payload = AuthTokenPayload(
        seed=seed,
        subject=subject_name,
        subject_type=subject_type_value,
    )
    auth_secret_key = os.environ['AUTH_KEY']
    return encode_jwt(payload, auth_secret_key)


def encode_jwt(payload: AuthTokenPayload, signature_key: str) -> str:
    payload_dict = dataclasses.asdict(payload)
    return jwt.encode(payload_dict, signature_key, algorithm="HS256")


class Migration(migrations.Migration):

    dependencies = [
        ('registry', '0022_delete_old_permissions'),
    ]

    operations = [
        migrations.RunPython(create_default_superuser),
    ]
