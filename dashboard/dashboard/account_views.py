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
from racetrack_commons.entities.users_client import UserAccountClient
from racetrack_commons.urls import get_external_pub_url
from dashboard.middleware import set_auth_token_cookie
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
        client = UserAccountClient(auth_token=get_auth_token(request))
        new_token = client.regen_user_token()
        request.session[RT_SESSION_USER_AUTH_KEY] = new_token
        response = HttpResponse(status=200)
        set_auth_token_cookie(new_token, response)
        return response

    except Exception as e:
        log_exception(ContextError('Regenerating user token failed', e))
        return JsonResponse({'error': str(e)}, status=500)
