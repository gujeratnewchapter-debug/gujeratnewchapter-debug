from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

admin.site.site_header = 'Ethiopian Startup School Admin'
admin.site.site_title = 'Ethiopian Startup School'
admin.site.index_title = 'Platform dashboard'

urlpatterns = [
    path('admin/', admin.site.urls),
    # Serve a simple favicon for browsers requesting /favicon.ico
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.svg', permanent=False)),
    path('api/auth/', include('accounts.urls')),
    path('api/', include('courses.urls')),
    path('api/', include('enrollments.urls')),
    path('api/', include('quizzes.urls')),
    path('api/', include('certificates.urls')),
    path('api/ai/', include('ai_tutor.urls')),
    path('api/', include('site_settings.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
