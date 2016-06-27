from __future__ import unicode_literals

from crispy_forms.layout import Reset, Submit
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm, PasswordChangeForm, SetPasswordForm
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse_lazy
from django.utils.encoding import force_text, force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _

from alpha.utils import getter, BaseFormHelper
from .tasks import send_email

UserModel = get_user_model()

DUPLICATE_EMAIL = _('Email is invalid or already taken.')
USERNAME_NOT_ALLOWED = _('Username is not allowed.')
USERNAME_ALREADY_TAKEN = _('Username is already taken.')
SPECIAL_EMAIL_SUFFIX = _(
    'Only special suffix of email address is allowed to register.')
TOS_REQUIRED = _('You must agree to the terms to register')


class SignupForm(BaseFormHelper, UserCreationForm):
    email = forms.EmailField(
        help_text=_('email address'),
        required=True
    )

    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Submit')))
        self.helper.add_input(Reset('reset', _('Reset')))

    class Meta(UserCreationForm.Meta):
        model = UserModel
        fields = [
            UserModel.USERNAME_FIELD,
            'email',
            'password1',
            'password2'
        ]
        required_css_class = 'required'

    def clean_email(self):
        email = self.cleaned_data['email']
        if getter('ACCOUNT_UNIQUE_EMAIL'):
            if UserModel.objects.filter(email__iexact=email):
                raise forms.ValidationError(DUPLICATE_EMAIL)
        email_suffix = email.split('@')[-1]
        enabled_suffix = getter('ACCOUNT_SUFFIX_ENABLED')
        disabled_suffix = getter('ACCOUNT_SUFFIX_DISABLED')
        if (enabled_suffix and email_suffix not in enabled_suffix) or disabled_suffix and email_suffix in disabled_suffix:
            raise forms.ValidationError(SPECIAL_EMAIL_SUFFIX)
        return self.cleaned_data['email']

    def clean_username(self):
        if self.cleaned_data['username'].lower() in getter('ACCOUNT_FORBIDDEN_USERNAMES'):
            raise forms.ValidationError(USERNAME_NOT_ALLOWED)
        try:
            user = UserModel.objects.get(
                username__iexact=self.cleaned_data['username'])
        except UserModel.DoesNotExist:
            pass
        else:
            raise forms.ValidationError(USERNAME_ALREADY_TAKEN)
        return self.cleaned_data['username']


class SignupFormTermsOfService(SignupForm):
    tos = forms.BooleanField(
        widget=forms.CheckboxInput,
        label=_('I have read and agree to the Terms of Service'),
        error_messages={
            'required': TOS_REQUIRED,
        }
    )


class LoginForm(BaseFormHelper, AuthenticationForm):
    remember = forms.BooleanField(
        widget=forms.CheckboxInput(),
        required=False,
        label=_('Remember me for %(days)d') % {
            'days': getter('ACCOUNT_REMEMBER_ME_DAYS')}
    )

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Login')))


class EditProfileForm(BaseFormHelper, forms.ModelForm):

    class Meta:
        model = UserModel
        exclude = ['password', 'last_login', 'is_superuser', 'groups', 'user_permissions',
                   'is_staff', 'is_active', 'date_joined', 'email_confirmed']

    def __init__(self, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        if getter('ACCOUNT_CHANGE_USERNAME_DISABLED'):
            self.fields['username'].widget.attrs['readonly'] = True
        self.helper.add_input(Submit('submit', _('Save')))


class MyPasswordChangeForm(BaseFormHelper, PasswordChangeForm):

    def __init__(self, *args, **kwargs):
        super(MyPasswordChangeForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Save')))


class MyPasswordResetForm(BaseFormHelper, PasswordResetForm):

    def __init__(self, *args, **kwargs):
        super(MyPasswordResetForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Reset my password')))

    def save(self, domain_override=None, subject_template_name=None, email_template_name=None,
             use_https=False, token_generator=None,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        email = self.cleaned_data['email']
        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'user': user,
                'protocol': 'https' if use_https else 'http',
                'token_url': reverse_lazy('account_password_reset_confirm', kwargs={
                    'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': user.token.last().token,
                })
            }
            if extra_email_context is not None:
                context.update(extra_email_context)
            send_email.delay(subject_template_name, email_template_name,
                             context, from_email, user.email,
                             html_email_template_name=html_email_template_name)


class MySetPasswordForm(BaseFormHelper, SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super(MySetPasswordForm, self).__init__(*args, **kwargs)
        self.helper.add_input(Submit('submit', _('Save new password')))
