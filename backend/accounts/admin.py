from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .forms import AdminUserChangeForm
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    list_display = ('username', 'email', 'role', 'is_email_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_email_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('Instructor profile', {
            'description': 'Instructor photos are uploaded here by an administrator and appear on course pages.',
            'fields': ('role', 'avatar', 'bio'),
        }),
        ('Platform access', {
            'fields': ('phone_number', 'is_email_verified', 'two_factor_enabled'),
        }),
    )
