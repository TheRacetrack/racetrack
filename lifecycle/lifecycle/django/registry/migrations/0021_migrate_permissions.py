from typing import Optional, List
import dataclasses
from dataclasses import dataclass
import os
import uuid

import jwt
from django.conf import settings
from django.db import migrations


def migrate_old_permissions(apps, schema_editor):
    UserProfile = apps.get_model('registry', 'UserProfile')
    JobFamily = apps.get_model('registry', 'JobFamily')
    Esc = apps.get_model('registry', 'Esc')
    AuthSubject = apps.get_model('registry', 'AuthSubject')
    AuthResourcePermission = apps.get_model('registry', 'AuthResourcePermission')

    # Users: create auth subjects grant default permissions
    for user_profile in UserProfile.objects.all():
        user = user_profile.user
        try:
            auth_subject = AuthSubject.objects.get(user=user)
        except AuthSubject.DoesNotExist:
            auth_subject = AuthSubject()
            auth_subject.user = user
            auth_subject.active = True
            auth_subject.token = generate_auth_token(user.username, 'user')
        auth_subject.save()

        grant_auth_permissions(auth_subject, AuthResourcePermission, 'read_job')
        grant_auth_permissions(auth_subject, AuthResourcePermission, 'call_job')
        grant_auth_permissions(auth_subject, AuthResourcePermission, 'deploy_new_family')
        grant_auth_permissions(auth_subject, AuthResourcePermission, 'deploy_job')

    # ESC
    for esc in Esc.objects.all():
        try:
            auth_subject = AuthSubject.objects.get(esc=esc)
        except AuthSubject.DoesNotExist:
            auth_subject = AuthSubject()
            auth_subject.esc = esc
        auth_subject.token = esc.esc_auth
        auth_subject.save()

        for allowed_family in esc.allowed_job_families.all():
            grant_auth_permissions_to_family(auth_subject, AuthResourcePermission, allowed_family, 'call_job')

    # create Job Families auth subjects
    for family in JobFamily.objects.all():
        try:
            auth_subject = AuthSubject.objects.get(job_family=family)
        except AuthSubject.DoesNotExist:
            auth_subject = AuthSubject()
            auth_subject.job_family = family
        auth_subject.token = generate_auth_token(family.name, 'job_family')
        auth_subject.save()

    for family in JobFamily.objects.all():
        for source_family in family.allowed_job_families.all():
            source_subject = AuthSubject.objects.get(job_family=source_family)
            grant_auth_permissions_to_family(source_subject, AuthResourcePermission, family, 'call_job')


def grant_auth_permissions(
    auth_subject,
    AuthResourcePermission,
    scope: str,
):
    permission = AuthResourcePermission(
        auth_subject=auth_subject,
        all_resources=True,
        scope=scope,
    )
    permission.save()


def grant_auth_permissions_to_family(
    auth_subject,
    AuthResourcePermission,
    job_family,
    scope: str,
):
    permission = AuthResourcePermission(
        auth_subject=auth_subject,
        all_resources=False,
        job_family=job_family,
        scope=scope,
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
    subject_type_value,
) -> str:
    payload = AuthTokenPayload(
        seed=str(uuid.uuid4()),
        subject=subject_name,
        subject_type=subject_type_value,
    )
    auth_secret_key = os.environ['AUTH_KEY']
    return encode_jwt(payload, auth_secret_key)


def encode_jwt(payload: AuthTokenPayload, signature_key: str) -> str:
    payload_dict = dataclasses.asdict(payload)
    return jwt.encode(payload_dict, signature_key, algorithm="HS256")


def dataclass_to_dict(dt):
    data_dict = dataclasses.asdict(dt)
    return data_dict


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('registry', '0020_new_permissions_model'),
    ]

    operations = [
        migrations.RunPython(migrate_old_permissions),
    ]
