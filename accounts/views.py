from __future__ import unicode_literals

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.core.urlresolvers import reverse_lazy
from django.shortcuts import redirect
from django.utils.encoding import force_text, force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, FormView, UpdateView

from inventory.models import Host
from alpha.utils import add_message, getter, BasicInfoMixin, default_token_generator
from .forms import UserModel, SignupForm, EditProfileForm, LoginForm, MyPasswordChangeForm, MyPasswordResetForm, MySetPasswordForm
from .models import Token
from .tasks import send_email


class SignupView(BasicInfoMixin, CreateView):
    email_template_name = 'accounts/message/activation_email.txt'
    subject_template_name = 'accounts/message/activation_email_subject.txt'
    template_name = 'accounts/signup_form.html'
    template_name_signup_closed = 'accounts/signup_closed.html'
    form_class = SignupForm
    token_generator = default_token_generator
    success_url = None

    def dispatch(self, *args, **kwargs):
        if getter('ACCOUNT_SIGNUP_DISABLED', False):
            return self.close()
        return super(SignupView, self).dispatch(*args, **kwargs)

    def close(self):
        template_name = self.template_name_signup_closed
        response_kwargs = {
            'request': self.request,
            'template': template_name,
        }
        return self.response_class(**response_kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        if settings.ACCOUNT_ACTIVATION_REQUIRED:
            user.is_active = False
        if not self.get_any_users():
            user.is_superuser = True
            user.is_staff = True
        user.save()
        token_opts = {
            'token': self.token_generator.make_token(user),
            'token_type': 2,
            'user': user
        }
        Token.objects.create(**token_opts)
        send_email.delay(subject_template_name=self.subject_template_name,
                         email_template_name=self.email_template_name,
                         context=self.get_email_context(user),
                         from_email=settings.DEFAULT_FROM_EMAIL,
                         to_email=user.email)
        add_message(self.request, 'email_confirmation_sent', email=user.email)

        return super(SignupView, self).form_valid(form)

    def get_any_users(self):
        return UserModel._default_manager.last()

    def get_success_url(self):
        return self.success_url or self.get_redirect_field_value() or reverse_lazy(settings.ACCOUNT_SIGNUP_REDIRECT_URL)

    def get_email_context(self, user):
        use_https = self.request.is_secure()
        return {
            'protocol': 'https' if use_https else 'http',
            'email': user.email,
            'current_site': get_current_site(self.request),
            'token_url': reverse_lazy('account_confirm', kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': user.token.last().token,
            }),
            'user': user,
            'expiration_days': settings.ACCOUNT_TOKEN_EXPIRED_DAYS,
        }


class ConfirmEmailView(BasicInfoMixin, TemplateView):
    template_name = 'accounts/account_confirm.html'
    token_generator = default_token_generator

    def get(self, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        uidb64, token = kwargs['uidb64'], kwargs['token']
        assert uidb64 is not None and token is not None
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            user = None
        if user.token.last().expired(**kwargs):
            context['msg'] = _('OOPS! Something Wrong!')
        elif user is not None and self.token_generator.check_token(user, token):
            user.__dict__.update(**dict(is_active=True, email_confirmed=True))
            user.save()
            token = user.token.last()
            token.used = True
            token.save()
            context['msg'] = _('Congratulations!')
        else:
            context['msg'] = _('OOPS! Something Wrong!')
        return self.render_to_response(context)


class LoginView(BasicInfoMixin, FormView):
    template_name = 'accounts/login.html'
    form_class = LoginForm

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            add_message(self.request, 'already_login',
                        username=self.request.user.username)
            return redirect(self.get_success_url())
        return super(LoginView, self).get(*args, **kwargs)

    def get_success_url(self):
        return self.success_url or self.get_redirect_field_value() or settings.LOGIN_REDIRECT_URL

    def form_valid(self, form):
        self.login_user(form)
        self.after_login(form)
        return super(LoginView, self).form_valid(form)

    def login_user(self, form):
        auth.login(self.request, form.get_user())
        expiry = settings.ACCOUNT_REMEMBER_ME_DAYS * \
            86400 if form.cleaned_data.get('remember', None) else 0
        self.request.session.set_expiry(expiry)

    def after_login(self, form):
        pass


class LogoutView(BasicInfoMixin, TemplateView):
    template_name = 'accounts/logout.html'

    def get(self, *args, **kwargs):
        if not self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(LogoutView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            auth.logout(self.request)
            add_message(self.request, 'logout')
        return redirect(self.get_success_url())

    def get_success_url(self):
        return self.get_redirect_field_value() or settings.LOGOUT_REDIRECT_URL


class ProfileView(BasicInfoMixin, LoginRequiredMixin, UpdateView):
    form_class = EditProfileForm
    model = UserModel
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('account_profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        add_message(self.request, 'profile_updated')
        return super(ProfileView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super(ProfileView, self).get_context_data(**kwargs)
        ctx['host_set'] = self.get_object().host_set.all()
        return ctx


class ChangePasswordView(BasicInfoMixin, LoginRequiredMixin, FormView):
    template_name = 'accounts/password_change.html'
    form_class = MyPasswordChangeForm
    success_url = reverse_lazy('account_password_change')

    def get_form_kwargs(self):
        kwargs = super(ChangePasswordView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def form_valid(self, form):
        self.instance = form.save()
        if hasattr(auth, 'update_session_auth_hash'):
            auth.update_session_auth_hash(self.request, form.user)
        self.after_change_password()
        return super(ChangePasswordView, self).form_valid(form)

    def after_change_password(self):
        user = self.request.user
        if settings.ACCOUNT_NOTIFY_ON_PASSWORD_CHANGE:
            # send_email(**)
            pass
        add_message(self.request, 'password_changed')


class DeleteAccountView(LogoutView):
    template_name = 'accounts/delete.html'

    def post(self, *args, **kwargs):
        self.request.user.is_active = False
        self.request.user.save()
        auth.logout(self.request)
        add_message(self.request, 'account_delete',
                    expunge_hours=settings.ACCOUNT_DELETION_EXPUNGE_HOURS)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        ctx = super(DeleteAccountView, self).get_context_data(**kwargs)
        ctx['ACCOUNT_DELETION_EXPUNGE_HOURS'] = settings.ACCOUNT_DELETION_EXPUNGE_HOURS
        return ctx


class PasswordResetView(BasicInfoMixin, FormView):
    form_class = MyPasswordResetForm
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/message/password_reset.txt'
    subject_template_name = 'accounts/message/password_reset_subject.txt'
    token_generator = default_token_generator
    success_url = reverse_lazy('account_password_reset')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        for user in form.get_users(email):
            token_opts = {
                'token': self.token_generator.make_token(user),
                'token_type': 3,
                'user': user
            }
            Token.objects.create(**token_opts)
        opts = {
            'use_https': self.request.is_secure(),
            'token_generator': self.token_generator,
            'from_email': settings.DEFAULT_FROM_EMAIL,
            'email_template_name': self.email_template_name,
            'subject_template_name': self.subject_template_name,
            'request': self.request,
        }
        form.save(**opts)
        add_message(self.request, 'email_reset_sent', email=email)
        return super(PasswordResetView, self).form_valid(form)


class PasswordResetConfirmView(BasicInfoMixin, FormView):
    template_name = 'accounts/password_reset_token.html'
    template_name_fail = 'accounts/password_reset_token_fail.html'
    form_class = MySetPasswordForm
    token_generator = default_token_generator
    success_url = reverse_lazy('account_login')

    def get(self, request, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        ctx = self.get_context_data(form=form)
        if not self.token_generator.check_token(self.get_user(), self.kwargs['token']):
            return self.token_fail()
        if self.request.user.is_authenticated():
            auth.logout(self.request)
        return self.render_to_response(ctx)

    def get_user(self):
        try:
            uid = force_text(urlsafe_base64_decode(self.kwargs['uidb64']))
            user = UserModel._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            user = None
        return user

    def get_form_kwargs(self):
        kwargs = super(PasswordResetConfirmView, self).get_form_kwargs()
        kwargs.update({
            'user': self.get_user(),
        })
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(PasswordResetConfirmView, self).get_context_data(**kwargs)
        ctx.update({
            'uidb64': self.kwargs['uidb64'],
            'token': self.kwargs['token'],
        })
        return ctx

    def form_valid(self, form):
        form.save()
        token = self.get_user().token.last()
        token.used = True
        token.save()
        add_message(self.request, 'password_changed')
        return super(PasswordResetConfirmView, self).form_valid(form)

    def token_fail(self):
        response_kwargs = {
            "request": self.request,
            "template": self.template_name_fail,
            "context": self.get_context_data()
        }
        return self.response_class(**response_kwargs)
