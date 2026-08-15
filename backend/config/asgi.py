import os

from django.core.asgi import get_asgi_application

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Keep the app running without a hardcoded secret. The real key should be supplied through the environment.
if not OPENROUTER_API_KEY:
    print("WARNING: OPENROUTER_API_KEY is not set; external model calls will fail until the environment is configured.")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
