from django.urls import path

from . import views
from .docs import view_docs_index, view_doc_page, view_doc_plugin


app_name = 'dashboard'
urlpatterns = [
    path('', views.list_fatmen, name='list'),
    path('graph', views.dependencies_graph, name='graph'),
    path('portfolio', views.view_fatman_portfolio, name='portfolio'),
    path('activity', views.view_fatman_activity, name='activity'),
    path('api/delete-fatman/<fatman_name>/<fatman_version>', views.delete_fatman, name='delete_fatman'),
    path('api/redeploy-fatman/<fatman_name>/<fatman_version>', views.redeploy_fatman, name='redeploy_fatman'),
    path('api/reprovision-fatman/<fatman_name>/<fatman_version>', views.reprovision_fatman, name='reprovision_fatman'),
    path('fatman/logs/<fatman_name>/<fatman_version>', views.fatman_runtime_logs, name='fatman_runtime_logs'),
    path('fatman/build-logs/<fatman_name>/<fatman_version>', views.fatman_build_logs, name='fatman_build_logs'),
    path('docs/', view_docs_index, name='docs_index'),
    path('docs/file/<path:doc_path>', view_doc_page, name='doc_page'),
    path('docs/plugin/<str:plugin_name>', view_doc_plugin, name='doc_plugin'),
    path('register/', views.register, name='register'),
    path('registered', views.registered, name='registered'),
    path('profile', views.user_profile, name='profile'),
    path('plugin/upload', views.upload_plugin, name='upload-plugin'),
]
