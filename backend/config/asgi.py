import os

from django.core.asgi import get_asgi_application

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
