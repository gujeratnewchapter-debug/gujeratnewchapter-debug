import os

# Do NOT hardcode secrets in source. Read the OpenRouter API key from
# an environment variable named `OPENROUTER_API_KEY`.
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
