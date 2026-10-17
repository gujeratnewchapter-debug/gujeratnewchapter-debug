from threading import RLock
from time import monotonic

from .models import FeatureFlag


CACHE_TTL_SECONDS = 30
_flag_cache = {}
_cache_lock = RLock()


def invalidate_flag_cache(key=None):
    with _cache_lock:
        if key is None:
            _flag_cache.clear()
        else:
            _flag_cache.pop(key, None)


def is_enabled(key):
    now = monotonic()
    with _cache_lock:
        cached = _flag_cache.get(key)
        if cached and cached[0] > now:
            return cached[1]

    enabled = FeatureFlag.objects.filter(key=key, is_enabled=True).exists()
    with _cache_lock:
        _flag_cache[key] = (now + CACHE_TTL_SECONDS, enabled)
    return enabled
