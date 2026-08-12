"""
Branded transactional email helpers. Every email uses the school name and
sender identity from SiteSettings so the school's name appears even when a
user signed up via Google (per the requirement: "even with google should
use the school name").
"""
import secrets
from django.core.mail import EmailMultiAlternatives
from django.conf import settings as django_settings
from site_settings.models import SiteSettings
from .models import EmailVerificationToken


def generate_and_send_verification_email(user, request=None):
    site = SiteSettings.load()

    token_obj, _ = EmailVerificationToken.objects.get_or_create(
        user=user, defaults={'token': secrets.token_urlsafe(32)}
    )
    if EmailVerificationToken.objects.filter(user=user).exists() and not token_obj.token:
        token_obj.token = secrets.token_urlsafe(32)
        token_obj.save()

    frontend_base = getattr(django_settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
    verify_url = f"{frontend_base}/verify-email?token={token_obj.token}"

    subject = site.email_verification_subject
    from_email = f"{site.email_sender_name} <{django_settings.DEFAULT_FROM_EMAIL}>"

    text_body = (
        f"Hi {user.first_name or user.username},\n\n"
        f"Welcome to {site.school_name}! Please confirm your email address by "
        f"opening the link below:\n\n{verify_url}\n\n"
        f"If you didn't create this account, you can ignore this email.\n\n"
        f"— {site.school_name}"
    )
    html_body = f"""
    <div style="font-family: sans-serif; max-width: 480px; margin: auto;">
      <h2 style="color:#111;">{site.school_name}</h2>
      <p>Hi {user.first_name or user.username},</p>
      <p>Welcome to <strong>{site.school_name}</strong>! Please confirm your email address:</p>
      <p><a href="{verify_url}" style="background:#6366F1;color:#fff;padding:10px 18px;
         border-radius:8px;text-decoration:none;display:inline-block;">Verify email</a></p>
      <p style="color:#666;font-size:13px;">If the button doesn't work, copy this link:<br>{verify_url}</p>
      <p style="color:#999;font-size:12px;">— {site.school_name}</p>
    </div>
    """

    msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)
    return token_obj
