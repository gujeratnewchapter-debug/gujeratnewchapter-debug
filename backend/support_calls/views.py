import hashlib
import secrets
from datetime import timedelta
from hmac import compare_digest
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .livekit import create_support_call_token
from .models import SupportCallRequest
from .permissions import IsSuperAdmin
from .serializers import SupportCallAdminSerializer, SupportCallCapabilitySerializer, SupportCallCreateSerializer
from .throttles import (
    SupportCallAdminTokenThrottle,
    SupportCallCreateThrottle,
    SupportCallStatusThrottle,
    SupportCallTokenThrottle,
)


REQUEST_TTL = timedelta(minutes=10)


def _capability_digest(capability):
    return hashlib.sha256(capability.encode('utf-8')).hexdigest()


def _requester_label(user):
    return ' '.join((user.first_name or '', user.last_name or '')).strip()


def _public_status(call):
    return {
        'call_id': str(call.id),
        'status': call.status,
        'mode': call.mode,
        'display_name': call.display_name,
        'accepted_at': call.accepted_at,
        'expires_at': call.expires_at,
    }


def _livekit_is_configured():
    livekit_url = urlparse(settings.LIVEKIT_URL)
    return bool(
        livekit_url.scheme in ('ws', 'wss')
        and livekit_url.netloc
        and settings.LIVEKIT_API_KEY
        and settings.LIVEKIT_API_SECRET
    )


def _no_store_response(data, response_status=None):
    response = Response(data, status=response_status)
    response['Cache-Control'] = 'no-store'
    return response


def _make_token(call, identity, is_admin=False):
    if not _livekit_is_configured():
        return None
    try:
        token = create_support_call_token(call.room_name, identity, call.mode, is_admin=is_admin)
    except ValueError:
        return None
    return {'token': token, 'url': settings.LIVEKIT_URL}


class SupportCallRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SupportCallCreateThrottle]
    throttle_scope = 'support_call_create'

    def post(self, request):
        if request.user.is_authenticated and (
            request.user.is_super_admin or getattr(request.user, 'role', None) != 'student'
        ):
            return Response({'detail': 'Only students can request a support call while signed in.'}, status=403)

        serializer = SupportCallCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        requester = request.user if request.user.is_authenticated else None
        display_name = values['display_name']
        email = values['email'].strip().lower()
        if requester:
            email = (requester.email or '').strip().lower()
            if not email:
                return Response({'detail': 'Add an email address to your account before requesting a call.'}, status=400)
            display_name = _requester_label(requester) or display_name

        capability = secrets.token_urlsafe(32)
        call_id = secrets.token_hex(16)
        call = SupportCallRequest.objects.create(
            requester=requester,
            display_name=display_name,
            email=email,
            question=values.get('question', ''),
            mode=values['mode'],
            capability_hash=_capability_digest(capability),
            room_name=f'support-{call_id}',
            expires_at=timezone.now() + REQUEST_TTL,
        )
        return _no_store_response({
            'call_id': str(call.id),
            'capability': capability,
            'status': call.status,
            'expires_at': call.expires_at,
        }, response_status=status.HTTP_201_CREATED)


class SupportCallStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SupportCallStatusThrottle]
    throttle_scope = 'support_call_status'

    def post(self, request):
        serializer = SupportCallCapabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        call = SupportCallRequest.objects.filter(pk=values['call_id']).first()
        if call is None or not compare_digest(call.capability_hash, _capability_digest(values['capability'])):
            return Response({'detail': 'Support call not found.'}, status=404)
        call.expire_if_needed()
        return _no_store_response(_public_status(call))


class SupportCallTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [SupportCallTokenThrottle]
    throttle_scope = 'support_call_token'

    def post(self, request):
        serializer = SupportCallCapabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        call = SupportCallRequest.objects.filter(pk=values['call_id']).first()
        if call is None or not compare_digest(call.capability_hash, _capability_digest(values['capability'])):
            return Response({'detail': 'Support call not found.'}, status=404)
        call.expire_if_needed()
        if call.status != SupportCallRequest.Status.ACCEPTED:
            return Response({'detail': f'This call is {call.status}; a connection token is not available.'}, status=409)
        credentials = _make_token(call, f'support-caller-{call.pk.hex}')
        if credentials is None:
            return Response({'detail': 'Live support calling is not configured yet. Please contact support or try again later.'}, status=503)
        return _no_store_response(credentials)


class SupportCallAdminQueueView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        now = timezone.now()
        SupportCallRequest.objects.filter(
            status=SupportCallRequest.Status.PENDING,
            expires_at__lte=now,
        ).update(status=SupportCallRequest.Status.EXPIRED, updated_at=now)
        calls = SupportCallRequest.objects.filter(
            Q(status=SupportCallRequest.Status.PENDING, expires_at__gt=now)
            | Q(status=SupportCallRequest.Status.ACCEPTED)
        ).select_related('requester', 'handled_by')
        return _no_store_response(SupportCallAdminSerializer(calls, many=True).data)


class SupportCallAdminDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request, call_id):
        call = SupportCallRequest.objects.filter(pk=call_id).first()
        if call is None:
            return Response({'detail': 'Support call not found.'}, status=404)
        call.expire_if_needed()
        return _no_store_response(SupportCallAdminSerializer(call).data)


class SupportCallAdminActionView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request, call_id, action):
        if action == 'accept' and not _livekit_is_configured():
            return Response({'detail': 'Live support calling is not configured on the server.'}, status=503)
        now = timezone.now()
        with transaction.atomic():
            call = SupportCallRequest.objects.select_for_update().filter(pk=call_id).first()
            if call is None:
                return Response({'detail': 'Support call not found.'}, status=404)
            call.expire_if_needed(now)
            if action in ('accept', 'reject'):
                if call.status != SupportCallRequest.Status.PENDING:
                    return Response({'detail': f'This request is already {call.status}.'}, status=409)
                call.status = (
                    SupportCallRequest.Status.ACCEPTED if action == 'accept'
                    else SupportCallRequest.Status.REJECTED
                )
                call.handled_by = request.user
                if action == 'accept':
                    call.accepted_at = now
                else:
                    call.ended_at = now
            elif action == 'end':
                if call.status != SupportCallRequest.Status.ACCEPTED:
                    return Response({'detail': 'Only an accepted support call can be ended.'}, status=409)
                call.status = SupportCallRequest.Status.ENDED
                call.ended_at = now
                call.handled_by = request.user
            else:
                return Response({'detail': 'Unknown support call action.'}, status=404)
            call.save(update_fields=('status', 'handled_by', 'accepted_at', 'ended_at', 'updated_at'))
        return Response(_public_status(call))


class SupportCallAdminTokenView(APIView):
    permission_classes = [IsSuperAdmin]
    throttle_classes = [SupportCallAdminTokenThrottle]
    throttle_scope = 'support_call_admin_token'

    def post(self, request, call_id):
        call = SupportCallRequest.objects.filter(pk=call_id).first()
        if call is None:
            return Response({'detail': 'Support call not found.'}, status=404)
        call.expire_if_needed()
        if call.status != SupportCallRequest.Status.ACCEPTED:
            return Response({'detail': f'This call is {call.status}; a connection token is not available.'}, status=409)
        credentials = _make_token(call, f'support-admin-{request.user.pk}', is_admin=True)
        if credentials is None:
            return Response({'detail': 'Live support calling is not configured yet. Please try again later.'}, status=503)
        return _no_store_response(credentials)
