from django.urls import path

from .view import views
from .view import account
from .docs import view_docs_index, view_doc_page, view_doc_plugin


app_name = 'dashboard'
urlpatterns = [
    path('', views.list_jobs, name='list'),
    path('graph', views.dependencies_graph, name='graph'),
    path('portfolio', views.view_job_portfolio, name='portfolio'),
    path('activity', views.view_job_activity, name='activity'),
    path('api/delete-job/<job_name>/<job_version>', views.delete_job, name='delete_job'),
    path('api/redeploy-job/<job_name>/<job_version>', views.redeploy_job, name='redeploy_job'),
    path('api/reprovision-job/<job_name>/<job_version>', views.reprovision_job, name='reprovision_job'),
    path('job/logs/<job_name>/<job_version>', views.job_runtime_logs, name='job_runtime_logs'),
    path('job/build-logs/<job_name>/<job_version>', views.job_build_logs, name='job_build_logs'),
    path('docs/', view_docs_index, name='docs_index'),
    path('docs/file/<path:doc_path>', view_doc_page, name='doc_page'),
    path('docs/plugin/<str:plugin_name>', view_doc_plugin, name='doc_plugin'),
    path('administration', views.view_administration, name='administration'),
    path('profile', account.view_user_profile, name='profile'),
    path('plugin/upload', views.upload_plugin, name='upload_plugin'),
    path('plugin/config-editor/<plugin_name>/<plugin_version>', views.plugin_config_editor, name='plugin_config_editor'),
    path('api/plugin/delete/<plugin_name>/<plugin_version>', views.delete_plugin, name='delete_plugin'),
    path('api/plugin/write-config/<plugin_name>/<plugin_version>', views.write_plugin_config, name='write_plugin_config'),
    path('api/auth/token/user/regenerate', account.regenerate_user_token, name='regenerate_user_token'),
    path('api/auth/token/user/retrieve', account.retrieve_user_token, name='retrieve_user_token'),

    path('accounts/login/', account.view_login, name='login'),
    path('accounts/logout/', account.view_logout, name='logout'),
    path('register/', account.view_register, name='register'),
    path('reset_password/', account.view_password_reset, name='password_reset'),
    path('change_password/', account.view_change_password, name='change_password'),
]
