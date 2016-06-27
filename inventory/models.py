from __future__ import unicode_literals

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from accounts.models import User

STATUS = (
    (0, _('ok')),
    (1, _('warning')),
    (2, _('critical')),
    (3, _('unknown')),
    (4, _('abandoned')),
    (5, _('under maintenance')),
)

ENV = (
    (1, _('development')),
    (2, _('production'))
)

TYPE = (
    (1, _('physical machine')),
    (2, _('virtual machine')),
    (3, _('router')),
    (4, _('switch')),
    (5, _('firewall')),
    (6, _('unknown'))
)


class GeneralInfo(models.Model):
    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False)
    update_ts = models.DateTimeField(
        auto_now=True, null=True, verbose_name=_('update timestamp'))
    desc = models.CharField(
        max_length=128, blank=True, null=True, verbose_name=_('description'))

    class Meta:
        abstract = True


class Hostgroup(GeneralInfo):
    name = models.CharField(
        max_length=64, unique=True, verbose_name=_('hostgroup'))
    status = models.IntegerField(
        choices=STATUS, default=0, verbose_name=_('current status'))

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = _('hostgroup')


class Host(GeneralInfo):
    hostname = models.CharField(
        max_length=64, unique=True, verbose_name=_('hostname'))
    owner = models.ManyToManyField(User, blank=True, verbose_name=_('owner'))
    ipv4_address = models.GenericIPAddressField(
        blank=True, null=True, verbose_name=_('ipv4 address'))
    ipv6_address = models.GenericIPAddressField(
        blank=True, null=True, verbose_name=_('ipv6 address'))
    macaddress = models.CharField(
        max_length=32, blank=True, null=True, verbose_name=_('mac address'))
    port = models.IntegerField(default=22, verbose_name=_('ssh port'))
    group = models.ManyToManyField(
        Hostgroup, blank=True, help_text=_('belong to which hostgroup'))
    sudo_username = models.CharField(
        max_length=32, verbose_name=_('sudo user'))
    sudo_password = models.CharField(
        max_length=128, verbose_name=_('password of sudo user'))
    processor = models.CharField(
        max_length=64, blank=True, null=True, verbose_name=_('processor'))
    processor_count = models.IntegerField(
        blank=True, null=True, verbose_name=_('processor count'))
    product_name = models.CharField(
        max_length=64, blank=True, null=True, verbose_name=_('manufacturer model'))
    lsb_desc = models.CharField(
        max_length=64, blank=True, null=True, verbose_name=_('system distribution information'))
    disk_total = models.CharField(
        max_length=64, blank=True, null=True, verbose_name=_('disk total'))
    memtotal_mb = models.IntegerField(
        blank=True, null=True, verbose_name=_('memory total'))
    memfree_mb = models.IntegerField(
        blank=True, null=True, verbose_name=_('memory free'))
    asset_number = models.CharField(
        max_length=64, blank=True, null=True, verbose_name=_('asset number'))
    status = models.IntegerField(
        choices=STATUS, default=0, verbose_name=_('current status'))
    wk_env = models.IntegerField(
        choices=ENV, default=2, verbose_name=_('working environment'))
    mc_type = models.IntegerField(
        choices=TYPE, default=6, verbose_name=_('machine type'))
    sn = models.CharField(
        max_length=128, blank=True, null=True, verbose_name=_('serial number'))

    def __unicode__(self):
        return 'hostname: %s | ipv4_address: %s | owners: %s' % (
            self.hostname, self.ipv4_address,
            ','.join([owner.username for owner in self.owner.all()])
        )

    class Meta:
        verbose_name = verbose_name_plural = _('host')
