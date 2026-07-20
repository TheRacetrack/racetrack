from django.contrib import admin
from django.urls import include, path

from lifecycle.django.staticfiles import staticfiles_urlpatterns

urlpatterns = [
    path('lifecycle/', include([
        path('admin/', admin.site.urls),
    ])),
] + staticfiles_urlpatterns()
