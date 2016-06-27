from django.conf.urls import include, url
from .views import (SignupView,
                    ConfirmEmailView,
                    LoginView,
                    LogoutView,
                    ProfileView,
                    ChangePasswordView,
                    DeleteAccountView,
                    PasswordResetView,
                    PasswordResetConfirmView,
                    )

urlpatterns = [
    url(r'^signup/$', SignupView.as_view(), name='account_signup'),
    url(r'^confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]+:[0-9A-Za-z]+:[\S]+)/$',
        ConfirmEmailView.as_view(), name='account_confirm'),
    url(r'^profile/$', ProfileView.as_view(), name='account_profile'),
    url(r'^login/$', LoginView.as_view(), name='account_login'),
    url(r'^logout/$', LogoutView.as_view(), name='account_logout'),
    url(r'^password_change/$', ChangePasswordView.as_view(),
        name='account_password_change'),
    url(r'^delete/$', DeleteAccountView.as_view(), name='account_delete'),
    url(r'^password_reset/$', PasswordResetView.as_view(),
        name='account_password_reset'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]+:[0-9A-Za-z]+:[\S]+)/$',
        PasswordResetConfirmView.as_view(), name='account_password_reset_confirm'),
]
