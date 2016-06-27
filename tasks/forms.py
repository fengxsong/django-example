from __future__ import unicode_literals

import re
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Reset, Submit
from django import forms
from django.utils.translation import ugettext_lazy as _

from alpha.utils import BaseFormHelper, MyRunner
from inventory.models import Host
from .models import RunnerOption, Repo
from .tasks import repo_runner


class RepoForm(BaseFormHelper, forms.ModelForm):
    error_messages = {
        'password_mismatch': _("The two password fields didn't match."),
    }
    password2 = forms.CharField(label=_('Password confirmation'),
                                widget=forms.PasswordInput(),
                                strip=False,
                                help_text=_('Enter the same password as before, for verification.'))

    class Meta:
        model = Repo
        exclude = ['author', 'created', 'updated']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super(RepoForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Submit')))
        self.helper.add_input(Reset('reset', _('Reset')))

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch',
            )
        return password2


class RepoActionForm(BaseFormHelper, forms.Form):
    revision = forms.IntegerField(label=_('Update or Rollback?'),
                                  min_value=0,
                                  help_text=_('If left blank, action will be <code>UPDATE</code> to latest revision, \
                               else will be <code>ROLLBACK</code> to specified revision.'))

    def __init__(self, user, repo, *args, **kwargs):
        self.user = user
        self.repo = repo
        super(RepoActionForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Submit')))
        self.fields['revision'].initial = repo.revision

    def get_runner_kwargs(self, obj):
        revision = self.cleaned_data['revision']
        if revision == int(obj.revision):
            revision_opts = ''
        else:
            revision_opts = 'revision=%s' % revision
        runner_kwargs = {
            'task_name': _('action of %s' % obj.pk),
            'host_list': ','.join(host.hostname for host in obj.hosts.exclude(status__in=[2, 3, 4, 5])) + ',' + ','.join(hostgroup.name for hostgroup in obj.hostgroups.exclude(status__in=[2, 3, 4, 5])),
            'module_name': obj.opts.module_name,
            'module_args': 'repo={0} dest={1} username={2} password={3} {4}'.format(
                obj.url, obj.dest, obj.username, obj.password, revision_opts),
            'remote_user': obj.opts.remote_user,
            'become_method': obj.opts.get_become_method_display(),
            'become_user': obj.opts.become_user,
        }
        return runner_kwargs

    def save(self):
        runner_kwargs = self.get_runner_kwargs(self.repo)
        play_return = repo_runner.delay(self.user, self.repo, **runner_kwargs)
        return play_return


class CmdForm(BaseFormHelper, forms.Form):
    cmd = forms.CharField(label=_('Shell or Command'))
    host = forms.ModelMultipleChoiceField(
        queryset=Host.objects.exclude(status__in=[2, 3, 4, 5]),
        widget=forms.CheckboxSelectMultiple)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(CmdForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Go!')))
        self.opts = RunnerOption.objects.filter(module_name='shell').last()

    def clean_cmd(self):
        if not self.opts:
            raise forms.ValidationError(
                _('Please define shell runner options first.'))
        cmd = self.cleaned_data['cmd']
        if re.findall('rm|dd|restart|init|shutdown|reboot', cmd.lower()):
            raise forms.ValidationError(
                _('%(cmd)s is not permitted.'), params={'cmd': cmd})
        return cmd

    def get_runner_kwargs(self):
        cmd = self.cleaned_data['cmd']
        host = self.cleaned_data['host']
        runner_kwargs = {
            'task_name': 'exec command %s' % cmd,
            'host_list': ','.join(h.hostname for h in host),
            'module_name': self.opts.module_name,
            'module_args': cmd,
            'remote_user': self.opts.remote_user,
            'become_method': self.opts.get_become_method_display(),
            'become_user': self.opts.become_user,
        }
        return runner_kwargs

    def save(self):
        runner_kwargs = self.get_runner_kwargs()
        play_return = MyRunner(**runner_kwargs).run()
        return play_return
