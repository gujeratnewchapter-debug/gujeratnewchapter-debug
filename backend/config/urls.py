from pathlib import Path

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.views.generic.base import RedirectView


def api_root(request):
    return JsonResponse({
        'name': 'Ethiopian Startup School API',
        'status': 'ok',
        'health': '/health/',
        'courses': '/api/courses/',
    })


def favicon_svg(request):
    static_root = Path(settings.STATIC_ROOT)
    static_dirs = [Path(static_dir) for static_dir in settings.STATICFILES_DIRS]
    candidate_dirs = [static_root, *static_dirs]
    favicon_path = next(
        (directory / 'favicon.svg' for directory in candidate_dirs if (directory / 'favicon.svg').exists()),
        None,
    )
    if favicon_path is None:
        return JsonResponse({'detail': 'favicon not found'}, status=404)
    return serve(request, 'favicon.svg', document_root=str(favicon_path.parent))

admin.site.site_header = 'Ethiopian Startup School Admin'
admin.site.site_title = 'Ethiopian Startup School'
admin.site.index_title = 'Platform dashboard'

urlpatterns = [
    path('', api_root, name='api-root'),
    path('admin/', admin.site.urls),
    path('health/', include('config.health_urls')),
    path('favicon.svg', favicon_svg, name='favicon-svg'),
    path('favicon.ico', RedirectView.as_view(url='/favicon.svg', permanent=False)),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('courses.urls')),
    path('api/', include('enrollments.urls')),
    path('api/', include('quizzes.urls')),
    path('api/', include('certificates.urls')),
    path('api/ai/', include('ai_tutor.urls')),
    path('api/', include('site_settings.urls')),
    path('api/platform/', include('ess_platform.urls')),
]

# Local development serves filesystem media. Production returns Supabase
# Storage URLs through the configured S3-compatible storage backend.
if settings.MEDIA_URL.startswith('/') and not settings.SUPABASE_STORAGE_CONFIGURED:
    urlpatterns += [
        path(
            settings.MEDIA_URL.lstrip('/'),
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
