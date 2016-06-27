from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Department, User


class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc')


class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'dept', 'is_active')
    search_fields = ('username',)
    fieldsets = [
        (None, {'fields': [
         'username', 'first_name',  'last_name', 'email', 'tel', 'dept', 'desc', 'date_joined', 'mugshot']}),
        (_('Permission'), {'fields': [
         'is_superuser', 'is_staff', 'is_active']}),
    ]


admin.site.register(Department, DepartmentAdmin)
admin.site.register(User, UserAdmin)
