import uuid

from django.contrib.auth.models import User
from django.db import models

from racetrack_client.utils.time import now
from racetrack_commons.auth.scope import AuthScope
from racetrack_commons.entities.dto import JobStatus, DeploymentStatus, AsyncJobCallStatus


def new_uuid() -> str:
    return str(uuid.uuid4())


class JobFamily(models.Model):
    """Collection of Jobs generations with the same name (family name)"""
    class Meta:
        app_label = 'registry'
        verbose_name_plural = "Job families"

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    name = models.CharField(max_length=512, unique=True)

    def __str__(self):
        return f'{self.name}'


class Job(models.Model):
    class Meta:
        app_label = 'registry'
        unique_together = (('name', 'version'),)
        verbose_name_plural = "Jobs"

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    family = models.ForeignKey(JobFamily, on_delete=models.CASCADE)
    name = models.CharField(max_length=512)
    version = models.CharField(max_length=256)
    status = models.CharField(max_length=32, choices=[(tag.value, tag.value) for tag in JobStatus])
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)
    manifest = models.TextField(null=True, blank=True)
    internal_name = models.CharField(max_length=512, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    notice = models.TextField(null=True, blank=True)
    image_tag = models.CharField(max_length=256, null=True)
    deployed_by = models.CharField(max_length=256, null=True)
    last_call_time = models.DateTimeField(null=True, blank=True)
    infrastructure_target = models.CharField(max_length=256, null=True)
    # internal hostnames of the job replicas (eg. pods)
    replica_internal_names = models.TextField(null=True, blank=True)
    # exact name and version of a job type used to build this job
    job_type_version = models.CharField(max_length=256, blank=True)
    # Statistics of a Job seen by infrastructure
    infrastructure_stats = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f'{self.name} v{self.version}'

    def save(self, *args, **kwargs):
        if not self.error:
            self.error = None
        super().save(*args, **kwargs)


class Deployment(models.Model):
    class Meta:
        app_label = 'registry'
        indexes = [
            models.Index(fields=["update_time"], name="update_time_idx"),
        ]

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    status = models.CharField(max_length=32, choices=[(tag.value, tag.value) for tag in DeploymentStatus])
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)
    manifest = models.TextField()
    job_name = models.CharField(max_length=512)
    job_version = models.CharField(max_length=256)
    error = models.TextField(null=True, blank=True)
    deployed_by = models.CharField(max_length=256, null=True)
    build_logs = models.TextField(null=True, blank=True)
    phase = models.TextField(null=True, blank=True)
    image_name = models.TextField(null=True, blank=True)
    infrastructure_target = models.CharField(max_length=256, null=True)
    warnings = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.id}'


class Esc(models.Model):
    class Meta:
        app_label = 'registry'
        verbose_name = "External service consumer"
        verbose_name_plural = "External service consumers"

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid, editable=False)
    name = models.CharField(max_length=512)

    def __str__(self):
        return f'{self.name} ({self.id})'


class PublicEndpointRequest(models.Model):
    class Meta:
        app_label = 'registry'
        verbose_name_plural = 'Public endpoint requests'

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    job = models.ForeignKey(Job, on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=512)
    active = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.job} {self.endpoint}'


class TrashJob(models.Model):
    class Meta:
        app_label = 'registry'
        verbose_name_plural = "Trash Jobs"

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    name = models.CharField(max_length=512)
    version = models.CharField(max_length=256)
    status = models.CharField(max_length=32, choices=[(tag.value, tag.value) for tag in JobStatus])
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)
    delete_time = models.DateTimeField(default=now)
    manifest = models.TextField(null=True, blank=True)
    internal_name = models.CharField(max_length=512, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    image_tag = models.CharField(max_length=256, null=True)
    deployed_by = models.CharField(max_length=256, null=True)  # points to git_credentials.username
    last_call_time = models.DateTimeField(null=True, blank=True)
    infrastructure_target = models.CharField(max_length=256, null=True)
    age_days = models.DecimalField(max_digits=6, decimal_places=3)


class AuditLogEvent(models.Model):
    class Meta:
        app_label = 'registry'
        indexes = [
            models.Index(fields=["timestamp"], name="timestamp_idx"),
            models.Index(fields=["username_executor"], name="username_executor_idx"),
            models.Index(fields=["job_name"], name="job_name_idx"),
            models.Index(fields=["job_version"], name="job_version_idx"),
        ]

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    version = models.IntegerField(default=1)  # data structure version
    timestamp = models.DateTimeField(default=now)
    event_type = models.CharField(max_length=512)
    properties = models.TextField(null=True)
    username_executor = models.CharField(max_length=512, null=True)
    username_subject = models.CharField(max_length=512, null=True)
    job_name = models.CharField(max_length=512, null=True)
    job_version = models.CharField(max_length=256, null=True)


class AuthSubject(models.Model):
    class Meta:
        app_label = 'registry'

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    esc = models.ForeignKey(Esc, on_delete=models.CASCADE, null=True, blank=True)
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        if self.user is not None:
            return f'User: {self.user}'
        if self.esc is not None:
            return f'ESC: {self.esc}'
        if self.job_family is not None:
            return f'Job Family: {self.job_family}'
        return f'{self.id}'

    def subject_type(self) -> str:
        if self.user is not None:
            return 'User'
        if self.esc is not None:
            return 'ESC'
        if self.job_family is not None:
            return 'Job Family'
        return 'Unknown'


class AuthToken(models.Model):
    class Meta:
        app_label = 'registry'
        indexes = [
            models.Index(fields=["token"], name="token_idx"),
        ]

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    auth_subject = models.ForeignKey(AuthSubject, on_delete=models.CASCADE)
    token = models.CharField(max_length=1024)  # JWT token
    expiry_time = models.DateTimeField(null=True, blank=True)
    active = models.BooleanField(default=True)
    # last day the token was used for authentication
    last_use_time = models.DateTimeField(null=True, blank=True)


class AuthResourcePermission(models.Model):
    class Meta:
        app_label = 'registry'

    auth_subject = models.ForeignKey(AuthSubject, on_delete=models.CASCADE)
    # operation permitted to the subject
    scope = models.CharField(max_length=32, choices=[(tag.value, tag.value) for tag in AuthScope])
    # resource-scope: anything, job family, job, endpoint
    job_family = models.ForeignKey(JobFamily, on_delete=models.CASCADE, null=True, blank=True)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True)
    endpoint = models.CharField(max_length=256, null=True, blank=True)


class Setting(models.Model):
    class Meta:
        app_label = 'registry'
        verbose_name_plural = "Settings"

    name = models.CharField(max_length=512, primary_key=True)
    value = models.JSONField(null=True, blank=True)


class AsyncJobCall(models.Model):
    class Meta:
        app_label = 'registry'
        verbose_name_plural = "Async Job Calls"

    id = models.CharField(max_length=36, primary_key=True, default=new_uuid)
    status = models.CharField(max_length=32, choices=[(tag.value, tag.value) for tag in AsyncJobCallStatus])
    started_at = models.DateTimeField(default=now)
    ended_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    job_name = models.CharField(max_length=512)
    job_version = models.CharField(max_length=256)
    job_path = models.CharField(max_length=512, blank=True)
    request_method = models.CharField(max_length=32)
    request_url = models.CharField(max_length=512)
    request_headers = models.JSONField(null=True, blank=True)
    request_body = models.BinaryField(max_length=None, blank=True)
    response_status_code = models.IntegerField(null=True)
    response_headers = models.JSONField(null=True, blank=True)
    response_body = models.BinaryField(max_length=None, blank=True)
    attempts = models.IntegerField(default=0)
    pub_instance_addr = models.CharField(max_length=256, blank=True)
    retriable_error = models.BooleanField()

    def __str__(self):
        return self.id
