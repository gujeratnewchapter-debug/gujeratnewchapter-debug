from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
            token_claims = jwt.decode(token, options={'verify_signature': False})
        except Exception:
            return None

        is_simple_jwt = (
            token_claims.get('token_type') == 'access'
            and token_claims.get('user_id') is not None
            and token_claims.get('aud') != 'authenticated'
        )
        if is_simple_jwt:
            return None

        try:
            payload = self._decode_token(token)
        except Exception:
            payload = self._fetch_supabase_user(token)

        if not payload:
            raise AuthenticationFailed('Invalid or expired authentication token.')

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

    def _fetch_supabase_user(self, token):
        """Let Supabase validate tokens when local JWT verification is unavailable."""
        supabase_url = getattr(settings, 'SUPABASE_URL', '')
        anon_key = getattr(settings, 'SUPABASE_ANON_KEY', '')
        if not supabase_url or not anon_key:
            return None

        request = Request(
            f'{supabase_url}/auth/v1/user',
            headers={
                'Authorization': f'Bearer {token}',
                'apikey': anon_key,
            },
        )
        try:
            with urlopen(request, timeout=5) as response:
                user_data = json.loads(response.read().decode('utf-8'))
        except (HTTPError, URLError, ValueError, TimeoutError):
            return None

        if not user_data.get('id'):
            return None
        return {
            'sub': user_data['id'],
            'email': user_data.get('email'),
            'user_metadata': user_data.get('user_metadata') or {},
        }

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
        algorithm = jwt.get_unverified_header(token).get('alg')
        if not algorithm:
            raise AuthenticationFailed('Supabase token has no signing algorithm.')

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience='authenticated',
            options={'verify_aud': True},
        )
