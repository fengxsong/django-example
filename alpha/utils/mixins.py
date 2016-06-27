from __future__ import unicode_literals

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.sites.shortcuts import get_current_site
from django.http import JsonResponse
from django.views.generic import TemplateView

from .base import getter


class BasicInfoMixin(object):

    head_title = None
    redirect_field_name = REDIRECT_FIELD_NAME

    def get_context_data(self, **kwargs):
        ctx = super(BasicInfoMixin, self).get_context_data(**kwargs)
        redirect_field_name = self.get_redirect_field_name()
        ctx.update({
            'ACCOUNT_SIGNUP_DISABLED': getter('ACCOUNT_SIGNUP_DISABLED', False),
            'head_title': self.get_head_title() or self.head_title,
            'redirect_field_name': redirect_field_name,
            'redirect_field_value': self.get_redirect_field_value(),
            'site': get_current_site(self.request),
        })
        return ctx

    def get_redirect_field_name(self):
        return self.redirect_field_name

    def get_redirect_field_value(self):
        return self.request.POST.get(self.get_redirect_field_name(), self.request.GET.get(self.get_redirect_field_name(), None))

    def get_head_title(self):
        return None


class SuperuserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_superuser


class StaffuserRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        return self.request.user.is_staff


class JSONResponseMixin(object):

    def render_to_json_response(self, context, **response_kwargs):
        return JsonResponse(self.get_data(context), **response_kwargs)

    def get_data(self, context):
        return context


class JSONView(JSONResponseMixin, TemplateView):

    def render_to_response(self, context, **response_kwargs):
        return self.render_to_json_response(context, **response_kwargs)
