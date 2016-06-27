# -*- coding:utf-8 -*-
import logging
import os
import re
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import Http404
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, FormView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from alpha.utils import BasicInfoMixin, MyRunner, add_message, StaffuserRequiredMixin
from .forms import RepoForm, RepoActionForm, CmdForm
from .models import Repo, CmdResult
from .tasks import g_results

conv_dest = lambda x, y: x + os.path.sep + \
    y if x.endswith(os.path.sep) or not re.findall(y, x) else x


class RepoCreateView(StaffuserRequiredMixin, BasicInfoMixin, CreateView):
    template_name = 'tasks/repo_form.html'
    form_class = RepoForm
    success_url = reverse_lazy('tasks:repo_list')
    head_title = _('Create Repo')

    def form_valid(self, form):
        form.instance.author = self.request.user
        slug = form.cleaned_data['url'].split('/')[-1]
        dest = form.cleaned_data['dest']
        form.instance.dest = conv_dest(dest, slug)
        return super(RepoCreateView, self).form_valid(form)


class RepoListView(LoginRequiredMixin, BasicInfoMixin, ListView):
    template_name = 'tasks/repo_list.html'
    model = Repo
    search_parameter = 'q'
    paginate_by = 10
    head_title = _('Repo List')

    def get_context_data(self, **kwargs):
        ctx = super(RepoListView, self).get_context_data(**kwargs)
        ctx.update({
            'search_show': True,
            'search_term': self.search_term(),
        })
        return ctx

    def search_term(self):
        return self.request.GET.get(self.search_parameter, None)

    def search(self, qs):
        q = self.search_term()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(url__icontains=q)
            )
        return qs

    def get_queryset(self):
        qs = super(RepoListView, self).get_queryset()
        if self.search_term():
            qs = self.search(qs)
        return qs


class RepoDetailView(LoginRequiredMixin, BasicInfoMixin, DetailView, FormView):
    template_name = 'tasks/repo_detail.html'
    model = Repo
    form_class = RepoActionForm

    def get_head_title(self):
        return _('Detail of %s(%s)' % (self.object.pk, self.object.name))

    def get_form_kwargs(self):
        kwargs = super(RepoDetailView, self).get_form_kwargs()
        kwargs['repo'] = self.get_object()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        return reverse_lazy('tasks:repo_detail', kwargs={'pk': self.get_object().pk})

    def generate_results(self, task_results):
        results = {}
        for host, task_result in task_results.items():
            result = task_result._result.copy()
            _ = result.pop('invocation')
            results[host] = result
        return results

    def form_valid(self, form):
        play_return = form.save()
        add_message(self.request, 'task_sent')
        return super(RepoDetailView, self).form_valid(form)


class ExecCmdView(LoginRequiredMixin, BasicInfoMixin, FormView):
    template_name = 'tasks/exec_cmd.html'
    form_class = CmdForm
    success_url = reverse_lazy('tasks:exec_cmd')

    def get_context_data(self, **kwargs):
        ctx = super(ExecCmdView, self).get_context_data(**kwargs)
        ctx['shell_results'] = CmdResult.objects.all()[:10]
        return ctx

    def get_form_kwargs(self):
        kwargs = super(ExecCmdView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        ret_code, callback = form.save()
        mapping = {
            'host_ok': 'stdout',
            'host_failed': 'stderr',
            'host_unreachable': 'msg'
        }
        results = g_results(ret_code, callback,
                            func=lambda x: {h: r._result.get(
                                mapping[getattr(x, '__name__')]) for (h, r) in x().items()},
                            model=CmdResult,
                            cmd=form.cleaned_data['cmd'],
                            executor=self.request.user)
        logging.warning(results)
        return super(ExecCmdView, self).form_valid(form)
