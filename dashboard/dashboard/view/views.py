import collections
import logging
from typing import Dict, List

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import urlencode

from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception
from racetrack_client.utils.time import days_ago
from racetrack_commons.entities.audit import explain_audit_log_event
from racetrack_commons.entities.audit_client import AuditClient
from racetrack_commons.entities.dto import AuditLogEventDto, JobDto
from racetrack_commons.entities.job_client import JobRegistryClient
from racetrack_commons.entities.plugin_client import LifecyclePluginClient
from racetrack_commons.urls import get_external_pub_url


@login_required
def list_jobs(request):
    context = {
        'external_pub_url': get_external_pub_url(),
        'jobs': None,
    }
    try:
        frc = JobRegistryClient(auth_token=get_auth_token(request))
        jobs: List[JobDto] = frc.list_deployed_jobs()
        context['jobs'] = jobs
    except Exception as e:
        log_exception(ContextError('Getting jobs failed', e))
        context['error'] = str(e)
    return render(request, 'racetrack/list.html', context)


@login_required
def delete_job(request, job_name: str, job_version: str):
    try:
        frc = _get_job_registry_client(request)
        frc.delete_deployed_job(job_name, job_version)
    except Exception as e:
        log_exception(ContextError('Deleting job failed', e))
        return JsonResponse({'error': str(e)}, status=500)
    return HttpResponse(status=204)


@login_required
def redeploy_job(request, job_name: str, job_version: str):
    try:
        frc = _get_job_registry_client(request)
        frc.redeploy_job(job_name, job_version)
    except Exception as e:
        log_exception(ContextError('Redeploying job failed', e))
        return JsonResponse({'error': str(e)}, status=500)
    return HttpResponse(status=204)


@login_required
def reprovision_job(request, job_name: str, job_version: str):
    try:
        frc = _get_job_registry_client(request)
        frc.reprovision_job(job_name, job_version)
    except Exception as e:
        log_exception(ContextError('Reprovisioning job failed', e))
        return JsonResponse({'error': str(e)}, status=500)
    return HttpResponse(status=204)


@login_required
def job_runtime_logs(request, job_name: str, job_version: str):
    tail = int(request.GET.get('tail', 0))
    content = _get_job_registry_client(request).get_runtime_logs(job_name, job_version, tail)
    content = remove_ansi_sequences(content)
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


@login_required
def job_build_logs(request, job_name: str, job_version: str):
    tail = int(request.GET.get('tail', 0))
    content = _get_job_registry_client(request).get_build_logs(job_name, job_version, tail)
    content = remove_ansi_sequences(content)
    return HttpResponse(content, content_type='text/plain; charset=utf-8')


def _get_job_registry_client(request) -> JobRegistryClient:
    return JobRegistryClient(auth_token=get_auth_token(request))
