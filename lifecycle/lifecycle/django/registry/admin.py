import os
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.admin.options import (
    csrf_protect_m,
    HttpResponseRedirect,
)
from django.contrib.admin import SimpleListFilter

from .models import AuthResourcePermission, AuthSubject, PublicEndpointRequest, Job, Deployment, Esc, JobFamily, TrashJob, AuditLogEvent
from ...auth.subject import regenerate_auth_token_by_id


class JobFamilyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']


class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version', 'status', 'update_time', 'deployed_by')
    search_fields = ['name', 'version', 'deployed_by']
    list_filter = ['status', 'deployed_by', 'name']


class DeploymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'job_name', 'job_version', 'status', 'create_time', 'deployed_by', 'phase')
    search_fields = ['id', 'job_name', 'job_version', 'deployed_by']
    list_filter = ['status', 'deployed_by', 'job_name']


class PublicEndpointRequestAdmin(admin.ModelAdmin):
    list_display = ('get_job_name', 'get_job_version', 'endpoint', 'active')
    search_fields = ['endpoint']
    list_filter = ['job__name', 'endpoint', 'active']

    @admin.display(ordering='job__name', description='Job name')
    def get_job_name(self, obj):
        return obj.job.name

    @admin.display(ordering='job__version', description='Job version')
    def get_job_version(self, obj):
        return obj.job.version


class EscAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['id', 'name']


class RacetrackUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_active', 'is_staff', 'is_superuser')


class TrashJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'version', 'status', 'delete_time', 'deployed_by', 'age_days')
    search_fields = ['id', 'name', 'version', 'status', 'deployed_by']
    list_filter = ['status', 'deployed_by', 'name']


class AuditLogEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'event_type', 'username_executor', 'job_name', 'job_version')
    search_fields = ['id', 'event_type', 'username_executor', 'job_name', 'job_version']
    list_filter = ['event_type', 'username_executor', 'job_name']


class AuthSubjectTypeFilter(SimpleListFilter):
    title = 'Subject type'
    parameter_name = 'subject_type'
    possible_values = ['User', 'ESC', 'Job Family', 'Unknown']

    def lookups(self, request, model_admin):
        return [(value, value) for value in self.possible_values]

    def queryset(self, request, queryset):
        if self.value() == 'User':
            return queryset.filter(user__isnull=False)
        if self.value() == 'ESC':
            return queryset.filter(esc__isnull=False)
        if self.value() == 'Job Family':
            return queryset.filter(job_family__isnull=False)
        if self.value() == 'Unknown':
            return queryset.filter(user__isnull=True, esc__isnull=True, job_family__isnull=True)
        return queryset


class AuthSubjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject_type', 'user', 'esc', 'job_family', 'active', 'expiry_time')
    search_fields = ['user__username', 'esc__name', 'job_family__name', 'token']
    list_filter = ['active', AuthSubjectTypeFilter]
    change_form_template = 'admin/auth_subject_change_form.html'

    @csrf_protect_m
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and '_generate_token' in request.POST and object_id is not None:
            regenerate_auth_token_by_id(str(object_id))
            return HttpResponseRedirect(request.get_full_path())

        return admin.ModelAdmin.changeform_view(self, request, object_id, form_url, extra_context)

    def get_form(self, request, obj=None, **kwargs):
        form = super(AuthSubjectAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields['token'].widget.attrs['style'] = 'width: 90em;'
        return form


class AuthResourcePermissionTypeFilter(SimpleListFilter):
    title = 'Subject type'
    parameter_name = 'subject_type'
    possible_values = ['User', 'ESC', 'Job Family', 'Unknown']

    def lookups(self, request, model_admin):
        return [(value, value) for value in self.possible_values]

    def queryset(self, request, queryset):
        if self.value() == 'User':
            return queryset.filter(auth_subject__user__isnull=False)
        if self.value() == 'ESC':
            return queryset.filter(auth_subject__esc__isnull=False)
        if self.value() == 'Job Family':
            return queryset.filter(auth_subject__job_family__isnull=False)
        if self.value() == 'Unknown':
            return queryset.filter(auth_subject__user__isnull=True, auth_subject__esc__isnull=True, auth_subject__job_family__isnull=True)
        return queryset


class AuthResourcePermissionAdmin(admin.ModelAdmin):
    list_display = ('auth_subject', 'scope', 'job_family', 'job', 'endpoint')
    list_filter = [AuthResourcePermissionTypeFilter, 'scope', 'job_family', 'job', 'endpoint']
    search_fields = ['auth_subject__user__username', 'auth_subject__esc__name', 'auth_subject__job_family__name', 'scope', 'endpoint']
    autocomplete_fields = ['auth_subject', 'job_family', 'job']


admin.site.unregister(User)
admin.site.register(User, RacetrackUserAdmin)

admin.site.register(Job, JobAdmin)
admin.site.register(JobFamily, JobFamilyAdmin)
admin.site.register(Deployment, DeploymentAdmin)
admin.site.register(Esc, EscAdmin)
admin.site.register(PublicEndpointRequest, PublicEndpointRequestAdmin)
admin.site.register(TrashJob, TrashJobAdmin)
admin.site.register(AuditLogEvent, AuditLogEventAdmin)
admin.site.register(AuthSubject, AuthSubjectAdmin)
admin.site.register(AuthResourcePermission, AuthResourcePermissionAdmin)


admin.site.index_title = f"Site administration (db: {os.environ.get('DJANGO_DB_TYPE')})"
