from __future__ import unicode_literals

from hashlib import md5
from crispy_forms.helper import FormHelper
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core import signing
from django.utils.six import text_type
from django.utils.translation import ugettext_lazy as _

getter = lambda name, dflt=None: getattr(settings, name, dflt)


def add_message(request, keyword, extra_tags=None, **kwargs):
    if settings.MSGS.get(keyword):
        messages.add_message(
            request,
            settings.MSGS[keyword]['level'],
            settings.MSGS[keyword]['text'].format(**kwargs),
            extra_tags=extra_tags
        )


def generate_md5(string):
    if not isinstance(string, (str, text_type)):
        string = str(string)
    return md5(string).hexdigest()


class BaseFormHelper(object):

    def __init__(self, *args, **kwargs):
        super(BaseFormHelper, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-4'
        self.helper.form_tag = False


class TokenGenerator(object):

    def make_token(self, user):
        return signing.dumps(obj=getattr(user, user.USERNAME_FIELD))

    def check_token(self, user, token):
        if user.token.last().expired(token=token):
            return False
        try:
            username_field = signing.loads(
                token, max_age=settings.ACCOUNT_TOKEN_EXPIRED_DAYS * 86400)
            if username_field == getattr(user, user.USERNAME_FIELD):
                return True
        except signing.BadSignature:
            return False
        return False

default_token_generator = TokenGenerator()
