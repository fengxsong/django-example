from __future__ import unicode_literals

import datetime
from django.conf import settings
from django.contrib.auth.models import UserManager, AbstractUser
from django.core import signing
from django.core.urlresolvers import reverse_lazy
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from alpha.utils import generate_md5

class Department(models.Model):
    name = models.CharField(
        _('department name'), max_length=64, unique=True)
    desc = models.CharField(
        _('description of department'), max_length=128, blank=True, null=True)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = _('department')


def upload_to_mugshot(instance, filename):
    extension = filename.split('.')[-1].lower()
    hash = generate_md5(instance.pk)
    path = settings.ACCOUNT_MUGSHOT_PATH % {'username': instance.username,
                                            'id': instance.id,
                                            'date': instance.date_joined,
                                            'date_now': timezone.now().date()}
    return '%(path)s%(hash)s.%(extension)s' % {'path': path,
                                               'hash': hash,
                                               'extension': extension}


class SignupManager(UserManager):

    def _create_user(self, username, email, password, **extra_fields):
        if not email:
            raise ValueError(_('the account must have an email address'))
        return super(SignupManager, self)._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    dept = models.ForeignKey(
        Department, related_name='user', blank=True, null=True, on_delete=models.SET_NULL, verbose_name=_('department'))
    desc = models.CharField(
        max_length=128, blank=True, null=True, verbose_name=_('description')
    )
    email_confirmed = models.BooleanField(
        default=False, help_text=_('already confirmed email address'))
    mugshot = models.ImageField(
        upload_to=upload_to_mugshot, verbose_name=_('avatar'))
    position = models.CharField(max_length=32, verbose_name=_('position'))
    tel = models.CharField(
        _('contact Number'), max_length=16, blank=True, null=True)
    objects = SignupManager()

    def __unicode__(self):
        return '%s %s' % (self.username, self.position)

    def save(self, *args, **kwargs):
        try:
            this = User.objects.get(pk=self.pk)
            if this.mugshot != self.mugshot:
                this.mugshot.delete(save=False)
        except:
            pass
        super(User, self).save(*args, **kwargs)

    class Meta:
        verbose_name = verbose_name_plural = _('user')


class Token(models.Model):
    TOKEN_TYPE = (
        (1, _('account activation')),
        (2, _('email confirmation')),
        (3, _('forget password')),
        (4, _('unknown')),
    )
    token = models.CharField(max_length=64, editable=False,
                             verbose_name=_('token key'))
    sent_out_date = models.DateTimeField(
        _('the day token sent out'), default=timezone.now)
    token_type = models.IntegerField(choices=TOKEN_TYPE, default=5)
    user = models.ForeignKey(
        User, related_name='token', blank=True, null=True, on_delete=models.SET_NULL)
    used = models.BooleanField(default=False)

    def __unicode__(self):
        return '%s -> %s' % (self.user.username, self.token)

    def expired(self, **kwargs):
        expiration_days = datetime.timedelta(
            days=settings.ACCOUNT_TOKEN_EXPIRED_DAYS)
        if self.token != kwargs.get('token') or self.used or self.sent_out_date + expiration_days <= timezone.now():
            return True
        return False

    class Meta:
        verbose_name = verbose_name_plural = _('token')
