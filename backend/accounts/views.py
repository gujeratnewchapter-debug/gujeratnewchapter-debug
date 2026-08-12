from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .serializers import RegisterSerializer, UserSerializer
from .models import EmailVerificationToken
from .email_utils import generate_and_send_verification_email

User = get_user_model()


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
        role = request.data.get('role', User.Role.STUDENT)
        if not id_token_str:
            return Response({"detail": "id_token is required."}, status=400)

        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
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
                'role': role,
                'is_email_verified': True,  # Google already verified it
            },
        )
        if created:
            user.set_unusable_password()
            user.save()

        return Response({"user": UserSerializer(user, context={'request': request}).data, **_tokens_for_user(user)})


from .serializers import RegisterSerializer, UserSerializer, CustomTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user, context={'request': request}).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
