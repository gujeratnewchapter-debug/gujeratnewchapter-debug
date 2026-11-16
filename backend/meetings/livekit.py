from datetime import datetime, timedelta, timezone

import jwt


def create_livekit_access_token(
    room_name: str,
    identity: str,
    role: str = 'student',
    is_host: bool = False,
    display_name: str = '',
) -> str:
    """Create a short-lived LiveKit JWT server-side without exposing API secrets in the browser."""
    from django.conf import settings

    if not settings.LIVEKIT_API_KEY or not settings.LIVEKIT_API_SECRET:
        raise ValueError('LIVEKIT_API_KEY and LIVEKIT_API_SECRET must be configured.')

    now = datetime.now(timezone.utc)
    payload = {
        'iss': settings.LIVEKIT_API_KEY,
        'sub': identity,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=30)).timestamp()),
        'video': {
            'room': room_name,
            'roomJoin': True,
            'canPublish': True,
            'canSubscribe': True,
            'canPublishData': True,
            'canUpdateOwnMetadata': True,
        },
        'name': display_name or identity,
    }
    if is_host:
        payload['video']['roomAdmin'] = True

    return jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm='HS256')
