from functools import wraps

from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.views import PasswordChangeView
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import generic

from dashboard.cookie import set_auth_token_cookie, delete_auth_cookie
from racetrack_client.log.context_error import ContextError
from racetrack_client.log.exception import log_exception
from racetrack_client.utils.auth import RT_AUTH_HEADER
from racetrack_commons.auth.auth import UnauthorizedError
from racetrack_commons.auth.token import decode_jwt
from racetrack_commons.entities.dto import UserProfileDto
from racetrack_commons.entities.users_client import UserAccountClient


def login_required(view_func):

    def wrapped_view(request, *args, **kwargs):
        if settings.AUTH_REQUIRED:
            if not request.COOKIES.get(RT_AUTH_HEADER):
                return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
        return view_func(request, *args, **kwargs)

    return wraps(view_func)(wrapped_view)


def get_auth_token(request) -> str:
    auth_token = request.COOKIES.get(RT_AUTH_HEADER)
    if not auth_token and not settings.AUTH_REQUIRED:
        return ''
    if not auth_token:
        raise UnauthorizedError('no Auth Token set, please log in.')
    decode_jwt(auth_token)
    return auth_token


def view_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        try:
            user_profile: UserProfileDto = UserAccountClient().login_user(username, password)
            response = redirect('dashboard:jobs')
            set_auth_token_cookie(user_profile.token, response)
            return response
        except Exception as e:
            log_exception(ContextError('Login failed', e))
            return render(request, 'registration/login.html', {'error': str(e)})

    return render(request, 'registration/login.html', {})


def view_logout(request):
    response = redirect('dashboard:login')
    delete_auth_cookie(response)
    return response


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
def view_user_profile(request):
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
        response = HttpResponse(status=200)
        set_auth_token_cookie(new_token, response)
        return response

    except Exception as e:
        log_exception(ContextError('Regenerating user token failed', e))
        return JsonResponse({'error': str(e)}, status=500)
