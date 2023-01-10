from django.shortcuts import redirect
from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin

from dashboard.staticfiles import staticfiles_urlpatterns
from dashboard.health import live, ready

urlpatterns = [
    path('', lambda req: redirect('dashboard/')),
    re_path(r'^ikp-rt/dashboard/(?P<subpath>.*)', lambda req, subpath: redirect(f'/dashboard/{subpath}')),
    path('dashboard/', include([
        path('', include('dashboard.urls')),
        path('accounts/', include('django.contrib.auth.urls')),
        path('live', live),
        path('ready', ready),
    ])),
    path('live', live),
    path('ready', ready),
] + staticfiles_urlpatterns()

if settings.RUNNING_ON_LOCALHOST:
    urlpatterns += path('dashboard/admin/', admin.site.urls),
