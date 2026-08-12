import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

django.setup()


def list_patterns(patterns, prefix=''):
    out = []
    for p in patterns:
        if isinstance(p, URLPattern):
            route = prefix + (p.pattern._route if hasattr(p.pattern, '_route') else str(p.pattern))
            callback = p.callback
            callback_name = getattr(callback, '__name__', repr(callback))
            out.append((route, f"{callback.__module__}.{callback_name}"))
        else:
            route = prefix + (p.pattern._route if hasattr(p.pattern, '_route') else str(p.pattern))
            out.extend(list_patterns(p.url_patterns, route))
    return out

patterns = list_patterns(get_resolver().url_patterns)
for route, callback in patterns:
    print(f"{route} -> {callback}")
