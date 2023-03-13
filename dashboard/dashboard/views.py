import logging
import collections
from typing import Dict, List

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy, reverse
from django.views import generic
from django.utils.http import urlencode

from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception
from racetrack_client.utils.time import days_ago
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_commons.auth.token import decode_jwt
from racetrack_commons.entities.audit import explain_audit_log_event
from racetrack_commons.entities.audit_client import AuditClient
from racetrack_commons.entities.dto import AuditLogEventDto, JobDto
from racetrack_commons.entities.job_client import JobRegistryClient
from racetrack_commons.entities.plugin_client import LifecyclePluginClient
from racetrack_commons.entities.users_client import UserRegistryClient
from racetrack_commons.urls import get_external_pub_url
from dashboard.dashboard.middleware import set_auth_token_cookie
from dashboard.session import RT_SESSION_USER_AUTH_KEY
from dashboard.purge import enrich_jobs_purge_info
from dashboard.utils import login_required, remove_ansi_sequences


def get_auth_token(request) -> str:
    token = request.session.get(RT_SESSION_USER_AUTH_KEY, '')
    if not token and not settings.AUTH_REQUIRED:
        return ''
    try:
        decode_jwt(token)
        return token
    except UnauthorizedError as e:
        raise e


class RacetrackUserCreationForm(UserCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text += ' Use your email as username.'
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        username = self.cleaned_data['username']
        if "@" not in username:
            raise ValidationError("You have to pass email as username")
        return username


class RacetrackPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'


class RegisterView(generic.CreateView):
    form_class = RacetrackUserCreationForm
    success_url = reverse_lazy('dashboard:registered')
    template_name = 'registration/register.html'


class ChangePasswordView(PasswordChangeView):
    form_class = RacetrackPasswordChangeForm
    success_url = reverse_lazy('dashboard:profile')
    template_name = 'registration/change_password.html'


def register(request):
    request.session['registered'] = False
    return RegisterView.as_view()(request)


def change_password(request):
    return ChangePasswordView.as_view()(request)


def registered(request):
    if request.session.get('registered', False):
        return redirect('login')
    request.session['registered'] = True
    return render(request, 'registration/registered.html')


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
def user_profile(request):
    context = {
        'user': request.user,
    }
    try:
        context['user_auth'] = get_auth_token(request)
    except Exception as e:
        log_exception(ContextError('Getting user profile data failed', e))
        context['error'] = str(e)

    return render(request, 'racetrack/profile.html', context)

@login_required
def retrieve_user_token(request):
    try:
        token = get_auth_token(request)
    except Exception as e:
        log_exception(ContextError('Retrieving user token failed', e))
        return JsonResponse({'error': str(e)}, status=500)

    return HttpResponse(status=200, content=token)

@login_required
def regenerate_user_token(request):
    try:
        client = UserRegistryClient(auth_token=get_auth_token(request))
        new_token = client.regen_user_token()
        request.session[RT_SESSION_USER_AUTH_KEY] = new_token
        response = HttpResponse(status=200)
        set_auth_token_cookie(new_token, response)
        return response

    except Exception as e:
        log_exception(ContextError('Regenerating user token failed', e))
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def view_administration(request):
    context = {}
    try:
        plugin_client = LifecyclePluginClient()
        context['plugins'] = plugin_client.get_plugins_info()
        context['job_type_versions'] = plugin_client.get_job_type_versions()
        context['infrastructure_targets'] = plugin_client.get_infrastructure_targets()

        # Collect instances running on the same infrastructure
        _infrastructure_instances: dict = collections.defaultdict(list)
        for infrastructure_name, plugin_manifest in context['infrastructure_targets'].items():
            _infrastructure_instances[plugin_manifest['name']].append(infrastructure_name)
        infrastructure_instances: list[tuple[str, List[str]]] = sorted(_infrastructure_instances.items())

        context['infrastructure_instances'] = infrastructure_instances
    except Exception as e:
        log_exception(ContextError('Getting plugins data failed', e))
        context['error'] = str(e)

    return render(request, 'racetrack/administration.html', context)


@login_required
def upload_plugin(request):
    try:
        if request.method == 'POST' and 'plugin-file' in request.FILES and request.FILES['plugin-file']:
            plugin_file = request.FILES['plugin-file']
            file_bytes = plugin_file.read()
            filename = plugin_file.name
            client = LifecyclePluginClient(auth_token=get_auth_token(request))
            client.upload_plugin(filename, file_bytes)
            parameters = urlencode({
                'success': f'Plugin file uploaded: {filename}',
            })
        else:
            parameters = urlencode({
                'error': 'No file to upload',
            })
    except Exception as e:
        log_exception(ContextError('Uploading a plugin', e))
        parameters = urlencode({
            'error': str(e),
        })
    redirect_url = reverse('dashboard:administration')
    return redirect(f'{redirect_url}?{parameters}')


@login_required
def plugin_config_editor(request, plugin_name: str, plugin_version: str):
    context = {
        'plugin_name': plugin_name,
        'plugin_version': plugin_version,
    }
    try:
        plugin_client = LifecyclePluginClient(auth_token=get_auth_token(request))
        context['plugin_config'] = plugin_client.read_plugin_config(plugin_name, plugin_version)
    except Exception as e:
        log_exception(ContextError('Getting plugin data failed', e))
        context['error'] = str(e)
    return render(request, 'racetrack/plugin_config_editor.html', context)


@login_required
def delete_plugin(request, plugin_name: str, plugin_version: str):
    try:
        client = LifecyclePluginClient(auth_token=get_auth_token(request))
        client.delete_plugin(plugin_name, plugin_version)
    except Exception as e:
        log_exception(ContextError('Deleting plugin failed', e))
        return JsonResponse({'error': str(e)}, status=500)
    return HttpResponse(status=204)

@login_required
def write_plugin_config(request, plugin_name: str, plugin_version: str):
    try:
        client = LifecyclePluginClient(auth_token=get_auth_token(request))
        config_data = request.body.decode()
        client.write_plugin_config(plugin_name, plugin_version, config_data)
    except Exception as e:
        log_exception(ContextError('Updating plugin config failed', e))
        return JsonResponse({'error': str(e)}, status=500)
    return HttpResponse(status=200)

@login_required
def dependencies_graph(request):
    context = {}
    try:
        frc = JobRegistryClient(auth_token=get_auth_token(request))
        context['job_graph'] = frc.get_dependencies_graph()
    except Exception as e:
        logging.error(f'Building dependencies graph failed: {e}')
        context['error'] = str(e)
    return render(request, 'racetrack/graph.html', context)


@login_required
def view_job_portfolio(request):
    context = {
        'external_pub_url': get_external_pub_url(),
        'jobs': None,
    }
    try:
        frc = JobRegistryClient(auth_token=get_auth_token(request))
        jobs: List[JobDto] = frc.list_deployed_jobs()
        job_dicts: List[Dict] = enrich_jobs_purge_info(jobs)

        for job_dict in job_dicts:
            job_dict['update_time_days_ago'] = days_ago(job_dict['update_time'])
            job_dict['last_call_time_days_ago'] = days_ago(job_dict['last_call_time'])
            manifest: Dict = job_dict.get('manifest')
            job_dict['job_type_version'] = manifest.get('lang') if manifest else None

        context['jobs'] = job_dicts
    except Exception as e:
        log_exception(ContextError('Getting jobs failed', e))
        context['error'] = str(e)
    return render(request, 'racetrack/portfolio.html', context)


@login_required
def view_job_activity(request):
    filter_job_name = request.GET.get('job_name', '')
    filter_job_version = request.GET.get('job_version', '')
    filter_related_to_me = request.GET.get('related_to_me', '')
    context = {
        'filter_job_name': filter_job_name,
        'filter_job_version': filter_job_version,
        'filter_related_to_me': filter_related_to_me,
    }
    try:
        audit_client = AuditClient(auth_token=get_auth_token(request))
        events: List[AuditLogEventDto] = audit_client.filter_events(filter_related_to_me, filter_job_name, filter_job_version)

        event_dicts = []
        for event in events:
            event_dict = event.dict()
            event_dict['explanation'] = explain_audit_log_event(event)
            event_dicts.append(event_dict)

        context['events'] = event_dicts
    except Exception as e:
        log_exception(ContextError('Getting audit log events failed', e))
        context['error'] = str(e)
    return render(request, 'racetrack/activity.html', context)


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
    if not request.user.is_authenticated:
        return JobRegistryClient()
    return JobRegistryClient(auth_token=get_auth_token(request))
