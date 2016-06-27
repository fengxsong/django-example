from __future__ import unicode_literals

import uuid
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils import timezone

from accounts.models import User
from inventory.models import Host, Hostgroup

BECOME_METHOD = (
    (0, 'sudo'),
    (1, 'su'),
    (2, 'pbrun'),
    (3, 'pfexec'),
    (4, 'runas'),
    (5, 'doas'),
    (6, 'dzdo')
)


class RunnerOption(models.Model):
    name = models.CharField(max_length=128, unique=True)
    module_name = models.CharField(max_length=64)
    become_user = models.CharField(max_length=64, default='root')
    become_method = models.IntegerField(choices=BECOME_METHOD, default=1)
    remote_user = models.CharField(max_length=64, default='root')

    def __unicode__(self):
        return '%s -> %s' % (self.name, self.module_name)


class Repo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=32, verbose_name=_('repo name'))
    author = models.ForeignKey(User, related_name='repo_author')
    url = models.CharField(
        max_length=64,
        verbose_name=_('subversion URL to the repository'))
    username = models.CharField(max_length=32, verbose_name=_('username'))
    password = models.CharField(max_length=64, verbose_name=_('password'))
    revision = models.CharField(max_length=32, verbose_name=_('revision'))
    hosts = models.ManyToManyField(Host, blank=True)
    hostgroups = models.ManyToManyField(Hostgroup, blank=True)
    dest = models.CharField(max_length=128, verbose_name=_('absolute path'))
    opts = models.ForeignKey(RunnerOption)
    created = models.DateTimeField(_('date created'), auto_now_add=True)
    updated = models.DateTimeField(_('date updated'), auto_now=True)

    def __unicode__(self):
        return u'%s -> %s' % (self.name, self.url)

    class Meta:
        verbose_name = verbose_name_plural = _('repository')


class Result(models.Model):
    ret_code = models.IntegerField(
        default=0, verbose_name=_('play return code'))
    results = models.TextField()
    created = models.DateTimeField(_('date created'), auto_now_add=True)

    class Meta:
        abstract = True
        ordering = ['created']


class RepoResult(Result):
    repo = models.ForeignKey(Repo, related_name='results')
    executor = models.ForeignKey(
        User, null=True, related_name='repo_executor',
        editable=False, verbose_name=_('operation executor'))

    def __unicode__(self):
        return '%s -> %s' % (self.repo.id, self.ret_code)


class CmdResult(Result):
    cmd = models.TextField()
    executor = models.ForeignKey(
        User, null=True, related_name='cmd_executor',
        editable=False, verbose_name=_('operation executor'))

    def __unicode__(self):
        return self.cmd
