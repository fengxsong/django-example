from django.conf.urls import include, url

from .views import RepoCreateView, RepoListView, RepoDetailView, ExecCmdView

urlpatterns = [
    url(r'^repo/$', RepoListView.as_view(), name='repo_list'),
    url(r'^repo/create/$', RepoCreateView.as_view(), name='repo_create'),
    url(r'^repo/(?P<pk>[a-zA-Z0-9\-]+)/$',
        RepoDetailView.as_view(), name='repo_detail'),
    url(r'^exec_cmd/$', ExecCmdView.as_view(), name='exec_cmd'),
]
