from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Return a minimal readiness response without exposing configuration."""
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({'status': 'unhealthy'}, status=503)

    return JsonResponse({'status': 'ok'})