from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_email_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_active', 'is_email_verified')
    fieldsets = UserAdmin.fieldsets + (
        ('Platform Info', {'fields': ('role', 'phone_number', 'bio', 'avatar', 'is_email_verified', 'two_factor_enabled')}),
    )
