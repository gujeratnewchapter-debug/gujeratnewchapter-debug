from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.views.static import serve
from django.views.generic.base import RedirectView

admin.site.site_header = 'Ethiopian Startup School Admin'
admin.site.site_title = 'Ethiopian Startup School'
admin.site.index_title = 'Platform dashboard'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', include('config.health_urls')),
    # Serve a simple favicon for browsers requesting /favicon.ico
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.svg', permanent=False)),
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
