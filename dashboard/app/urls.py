from django.shortcuts import redirect
from django.urls import include, path, re_path

from dashboard.staticfiles import staticfiles_urlpatterns
from dashboard.health import live, ready

urlpatterns = [
    path('', lambda req: redirect('dashboard/')),
    re_path(r'^ikp-rt/dashboard/(?P<subpath>.*)', lambda req, subpath: redirect(f'/dashboard/{subpath}')),
    path('dashboard/', include([
        path('', include('dashboard.urls')),
        path('live', live),
        path('ready', ready),
    ])),
    path('live', live),
    path('ready', ready),
] + staticfiles_urlpatterns()
