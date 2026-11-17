import logging
import smtplib
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from .serializers import (
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
)
from .models import EmailVerificationToken
from .email_utils import generate_and_send_verification_email

User = get_user_model()
logger = logging.getLogger(__name__)


def _tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterView(generics.CreateAPIView):
    """
    Student/Instructor self-registration. Sends a branded verification email
    immediately after signup; the account works but is flagged unverified
    (is_email_verified=False) until the link is clicked.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(id=response.data['id'])
        generate_and_send_verification_email(user, request)
        return response


class VerifyEmailView(APIView):
    """Public endpoint hit by the link in the verification email."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        try:
            token_obj = EmailVerificationToken.objects.select_related('user').get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return Response({"detail": "Invalid or expired verification link."}, status=400)

        user = token_obj.user
        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])
        token_obj.delete()
        return Response({"detail": "Email verified successfully.", **_tokens_for_user(user)})


class ResendVerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.is_email_verified:
            return Response({"detail": "Email already verified."})
        generate_and_send_verification_email(request.user, request)
        return Response({"detail": "Verification email resent."})


class GoogleLoginView(APIView):
    """
    Accepts a Google ID token from the frontend (Google Identity Services),
    verifies it server-side, and creates/logs in the matching user.
    Google-signed-up users are auto-verified (Google already confirmed their
    email) but still see the school's branding everywhere else in the app.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        id_token_str = request.data.get('id_token')
        if not id_token_str:
            return Response({"detail": "id_token is required."}, status=400)

        try:
            from django.conf import settings as django_settings

            idinfo = google_id_token.verify_oauth2_token(
                id_token_str, google_requests.Request(), django_settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except Exception:
            return Response({"detail": "Invalid Google token."}, status=400)

        email = idinfo.get('email')
        if not email:
            return Response({"detail": "Google account has no email."}, status=400)

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': idinfo.get('given_name', ''),
                'last_name': idinfo.get('family_name', ''),
                'role': User.Role.STUDENT,
                'is_email_verified': True,  # Google already verified it
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        return Response({"user": UserSerializer(user, context={'request': request}).data, **_tokens_for_user(user)})


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        users = [
            user for user in User.objects.filter(email__iexact=email, is_active=True)
            if user.has_usable_password()
        ]

        try:
            for user in users:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = (
                    f'{settings.FRONTEND_BASE_URL.rstrip("/")}/reset-password?'
                    f'{urlencode({"provider": "django", "uid": uid, "token": token})}'
                )
                message = (
                    f'We received a request to reset the password for your Ethiopian Startup School account.\n\n'
                    f'Use this link to choose a new password:\n{reset_url}\n\n'
                    'If you did not request this, you can ignore this email.'
                )
                if send_mail(
                    'Reset your Ethiopian Startup School password',
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                ) != 1:
                    raise smtplib.SMTPException('Email backend did not accept the password reset message.')
        except (OSError, smtplib.SMTPException):
            logger.exception('Could not send a Django password reset email.')
            return Response(
                {'detail': 'Unable to send a password reset email right now. Please try again later.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            'detail': 'If an eligible account exists for that email, a password reset email will be sent.',
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset_confirm'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        password = serializer.validated_data['new_password']

        try:
            user_id = urlsafe_base64_decode(uid).decode()
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, TypeError, ValueError, OverflowError, UnicodeError):
            raise ValidationError({'detail': 'This password reset link is invalid or has expired.'})

        if not user.has_usable_password() or not default_token_generator.check_token(user, token):
            raise ValidationError({'detail': 'This password reset link is invalid or has expired.'})

        try:
            validate_password(password, user)
        except DjangoValidationError as error:
            raise ValidationError({'new_password': error.messages})

        user.set_password(password)
        user.save(update_fields=['password'])
        return Response({'detail': 'Password updated successfully.'})


class SessionSyncView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'user': UserSerializer(request.user, context={'request': request}).data,
            **_tokens_for_user(request.user),
        })


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
