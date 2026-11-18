from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


TOKEN_LIFETIME = timedelta(minutes=30)


def create_support_call_token(room_name, identity, mode, is_admin=False):
    """Issue a short-lived token limited to the requested media sources."""
    if not settings.LIVEKIT_URL or not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise ValueError('LiveKit is not configured.')
    if mode not in ('audio', 'video'):
        raise ValueError('Unsupported support call mode.')

    now = datetime.now(timezone.utc)
    video_grant = {
        'room': room_name,
        'roomJoin': True,
        'canPublish': True,
        'canPublishSources': ['microphone', 'camera'] if mode == 'video' else ['microphone'],
        'canPublishData': False,
        'canSubscribe': True,
    }
    if is_admin:
        video_grant['roomAdmin'] = True

    payload = {
        'iss': settings.LIVEKIT_API_KEY,
        'sub': identity,
        'iat': int(now.timestamp()),
        'exp': int((now + TOKEN_LIFETIME).timestamp()),
        'video': video_grant,
        'name': identity,
    }
    return jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm='HS256')
