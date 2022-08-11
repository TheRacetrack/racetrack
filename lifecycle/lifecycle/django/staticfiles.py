import os
import posixpath
import re

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.urls import re_path
from django.views.static import serve as static_serve


def staticfiles_urlpatterns():
    """
    Helper function to return a URL pattern for serving static files.
    Modified django.contrib.staticfiles.urls.staticfiles_urlpatterns
    """
    prefix = settings.STATIC_URL
    return _urls_static(prefix, view=_serve)


def _urls_static(prefix, view):
    if not prefix:
        raise ImproperlyConfigured("Empty static prefix not permitted")
    return [
        re_path(r'^%s(?P<path>.*)$' % re.escape(prefix.lstrip('/')), view),
    ]


def _serve(request, path, **kwargs):
    normalized_path = posixpath.normpath(path).lstrip('/')
    absolute_path = finders.find(normalized_path)
    if not absolute_path:
        if path.endswith('/') or path == '':
            raise Http404("Directory indexes are not allowed here.")
        raise Http404("'%s' could not be found" % path)
    document_root, path = os.path.split(absolute_path)
    return static_serve(request, path, document_root=document_root, **kwargs)
