from racetrack_client.manifest import Manifest
from racetrack_commons.auth.scope import AuthScope
from lifecycle.auth.authorize import authorize_resource_access, authorize_scope_access
from lifecycle.django.registry import models
from lifecycle.job.models_registry import job_family_exists


def check_deploy_permissions(auth_subject: models.AuthSubject, manifest: Manifest):
    if job_family_exists(manifest.name):
        authorize_resource_access(auth_subject, manifest.name, manifest.version, AuthScope.DEPLOY_JOB.value)
    else:
        authorize_scope_access(auth_subject, AuthScope.DEPLOY_NEW_FAMILY.value)
