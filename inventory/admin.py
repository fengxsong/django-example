from django.contrib import admin

from .models import Hostgroup, Host

admin.site.register(Hostgroup)
admin.site.register(Host)
