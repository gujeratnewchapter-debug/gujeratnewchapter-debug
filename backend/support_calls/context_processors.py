from django.conf import settings


def support_call_settings(_request):
    return {
        'support_call_frontend_url': settings.FRONTEND_BASE_URL.rstrip('/'),
        'support_call_admin_script_url': (
            f'{settings.STATIC_URL.rstrip("/")}/support_calls/admin_support_calls.js'
        ),
    }
