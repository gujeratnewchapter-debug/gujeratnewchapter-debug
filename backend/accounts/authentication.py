from __future__ import annotations

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()


class SupabaseJWTAuthentication(BaseAuthentication):
    """Validate the bearer token issued by Supabase Auth and map it to this app's user model."""

    keyword = 'Bearer'

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or len(auth) != 2:
            return None

        if auth[0].lower() != self.keyword.lower().encode():
            return None

        token = auth[1].decode('utf-8')

        try:
            payload = self._decode_token(token)
        except Exception as exc:  # pragma: no cover - DRF will surface the message
            raise AuthenticationFailed('Invalid or expired authentication token.') from exc

        sub = payload.get('sub')
        email = payload.get('email')
        if not sub:
            raise AuthenticationFailed('Supabase token is missing a user identifier.')

        user = User.objects.filter(supabase_user_id=sub).first()
        if user is None and email:
            user = User.objects.filter(email__iexact=email).first()

        if user is None:
            username_base = (email or f"supabase-{sub}").split('@')[0].replace(' ', '-')[:30] or 'supabase-user'
            username = username_base
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=email or f"{username}@placeholder.local",
                first_name=payload.get('user_metadata', {}).get('full_name', '').split(' ')[0] if isinstance(payload.get('user_metadata'), dict) else '',
                last_name=(payload.get('user_metadata', {}).get('full_name', '').split(' ', 1)[1] if isinstance(payload.get('user_metadata'), dict) and 'full_name' in payload.get('user_metadata') and ' ' in payload.get('user_metadata', {}).get('full_name', '') else ''),
                role=User.Role.STUDENT,
                supabase_user_id=sub,
                is_email_verified=True,
            )
            user.set_unusable_password()
            user.save(update_fields=['supabase_user_id', 'is_email_verified', 'role'])

        if user.supabase_user_id is None:
            user.supabase_user_id = sub
            user.save(update_fields=['supabase_user_id'])

        return (user, token)

    def _decode_token(self, token):
        if getattr(settings, 'SUPABASE_JWT_SECRET', ''):
            return jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=['HS256'],
                audience='authenticated',
                options={'verify_aud': True},
            )

        jwks_url = getattr(settings, 'SUPABASE_JWKS_URL', '')
        if not jwks_url:
            raise AuthenticationFailed('Supabase JWT verification is not configured on the server.')

        signing_key = jwt.PyJWKClient(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            audience='authenticated',
            options={'verify_aud': True},
        )
