import logging
import smtplib
from html import escape
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db.models import Q
from django.utils import timezone

from site_settings.models import SiteSettings

logger = logging.getLogger(__name__)


def send_meeting_invitations(meeting, invitees, require_acceptance=True):
    if settings.EMAIL_BACKEND.endswith('.console.EmailBackend'):
        logger.warning(
            'Meeting invitations for %s were not emailed because the console email backend is configured.',
            meeting.pk,
        )
        return {'sent': 0, 'failed': len(invitees), 'configured': False}

    site = SiteSettings.load()
    school_name = site.school_name
    sender_address = settings.DEFAULT_FROM_EMAIL
    if sender_address.endswith('@localhost') and settings.EMAIL_HOST_USER:
        sender_address = settings.EMAIL_HOST_USER
    from_email = f'{site.email_sender_name} <{sender_address}>'
    meeting_url = (
        f'{settings.FRONTEND_BASE_URL.rstrip("/")}/meetings/'
        f'{quote(str(meeting.pk), safe="")}'
    )
    scheduled_time = timezone.localtime(meeting.scheduled_start).strftime(
        '%A, %B %d, %Y at %I:%M %p %Z'
    )
    kind_label = meeting.get_kind_display()
    sent = 0
    failed = 0
    connection = get_connection(
        fail_silently=False,
        timeout=min(settings.EMAIL_TIMEOUT, 10),
    )
    try:
        connection.open()
    except (OSError, smtplib.SMTPException):
        logger.exception('Could not open the email connection for meeting %s.', meeting.pk)
        return {'sent': 0, 'failed': len(invitees), 'configured': True}

    try:
        for invitee in invitees:
            if not invitee.email:
                failed += 1
                logger.warning(
                    'Cannot send meeting invitation for meeting %s because an invitee has no email address.',
                    meeting.pk,
                )
                continue
            recipient_name = (
                f'{invitee.first_name} {invitee.last_name}'.strip() or invitee.username
            )
            host_name = meeting.host.get_full_name() or meeting.host.username
            subject = f'You are invited to a live meeting | {school_name}'
            acceptance_instructions = (
                'Sign in, open the meeting, and accept the invitation. You can join once '
                'the host starts the room.'
                if require_acceptance
                else 'Sign in with your ESS account and join the room when the host starts it.'
            )
            text_body = (
                f'Hello {recipient_name},\n\n'
                f'{host_name} invited you to a live meeting.\n\n'
                f'Meeting: {meeting.title}\n'
                f'Type: {kind_label}\n'
                f'Scheduled for: {scheduled_time}\n\n'
                f'{meeting.description.strip()}\n\n'
                f'{acceptance_instructions}\n\n'
                f'Open meeting: {meeting_url}\n\n'
                f'{school_name}'
            )
            html_body = f"""
        <div style="font-family:Arial,sans-serif;color:#172033;max-width:620px;margin:0 auto;padding:32px 24px;">
          <p style="margin:0;color:#52637d;font-size:13px;font-weight:700;letter-spacing:.08em;">{escape(school_name.upper())}</p>
          <h1 style="font-size:23px;margin:12px 0 20px;">You are invited to a live meeting</h1>
          <p style="font-size:15px;line-height:1.6;">Hello {escape(recipient_name)}, {escape(host_name)} invited you to join.</p>
          <div style="background:#f5f7fb;border-radius:12px;padding:18px 20px;margin:22px 0;">
            <p style="margin:0 0 10px;"><strong>Meeting:</strong> {escape(meeting.title)}</p>
            <p style="margin:0 0 10px;"><strong>Type:</strong> {escape(kind_label)}</p>
            <p style="margin:0;"><strong>Scheduled for:</strong> {escape(scheduled_time)}</p>
          </div>
          <p style="font-size:15px;line-height:1.6;">{escape(meeting.description.strip())}</p>
          <p style="font-size:15px;line-height:1.6;">{escape(acceptance_instructions)}</p>
          <p style="margin:24px 0;">
            <a href="{escape(meeting_url, quote=True)}" style="display:inline-block;background:#176b55;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:700;">
              Open meeting
            </a>
          </p>
          <p style="color:#68758a;font-size:13px;">Sign in with the ESS account registered to this email address.</p>
        </div>
        """
            message = EmailMultiAlternatives(
                subject,
                text_body,
                from_email,
                [invitee.email],
                connection=connection,
            )
            message.attach_alternative(html_body, 'text/html')
            try:
                delivered = message.send(fail_silently=False)
                sent += delivered
                if not delivered:
                    failed += 1
            except (OSError, smtplib.SMTPException):
                failed += 1
                logger.exception(
                    'Failed to send meeting invitation for meeting %s to an invitee.',
                    meeting.pk,
                )
    finally:
        try:
            connection.close()
        except (OSError, smtplib.SMTPException):
            logger.exception('Could not close the email connection for meeting %s.', meeting.pk)

    return {'sent': sent, 'failed': failed, 'configured': True}


def notify_admins_of_student_booking(meeting):
    user_model = get_user_model()
    recipients = list(
        user_model.objects.filter(
            Q(role=user_model.Role.SUPER_ADMIN) | Q(is_staff=True),
            is_active=True,
        )
        .exclude(email='')
        .values_list('email', flat=True)
        .distinct()
    )
    if not recipients:
        logger.warning('No active admin email recipients for student meeting %s.', meeting.pk)
        return 0

    site = SiteSettings.load()
    school_name = site.school_name
    student_name = (
        f'{meeting.host.first_name} {meeting.host.last_name}'.strip()
        or meeting.host.username
    )
    scheduled_time = timezone.localtime(meeting.scheduled_start).strftime('%A, %B %d, %Y at %I:%M %p %Z')
    meeting_url = f'{settings.FRONTEND_BASE_URL.rstrip("/")}/meetings'
    subject = f'New student meeting request | {school_name}'
    text_body = (
        f'A student has booked a private live meeting.\n\n'
        f'Student: {student_name}\n'
        f'Email: {meeting.host.email}\n'
        f'Meeting: {meeting.title}\n'
        f'Scheduled for: {scheduled_time}\n\n'
        f'Open the ESS meetings schedule to review and join:\n{meeting_url}\n\n'
        f'Please sign in with your administrator account to access the meeting.\n\n'
        f'{school_name}'
    )
    html_body = f"""
    <div style="font-family:Arial,sans-serif;color:#172033;max-width:620px;margin:0 auto;padding:32px 24px;">
      <div style="border-bottom:1px solid #e5e9f0;padding-bottom:18px;margin-bottom:24px;">
        <p style="margin:0;color:#52637d;font-size:13px;font-weight:700;letter-spacing:.08em;">{escape(school_name.upper())}</p>
        <h1 style="font-size:23px;margin:12px 0 0;">New private meeting booking</h1>
      </div>
      <p style="font-size:15px;line-height:1.6;">A student has booked a live meeting with the administration team.</p>
      <div style="background:#f5f7fb;border-radius:12px;padding:18px 20px;margin:22px 0;">
        <p style="margin:0 0 10px;"><strong>Student:</strong> {escape(student_name)}</p>
        <p style="margin:0 0 10px;"><strong>Email:</strong> {escape(meeting.host.email)}</p>
        <p style="margin:0 0 10px;"><strong>Meeting:</strong> {escape(meeting.title)}</p>
        <p style="margin:0;"><strong>Scheduled for:</strong> {escape(scheduled_time)}</p>
      </div>
      <p style="font-size:15px;line-height:1.6;">Please open the schedule to review the booking and join the room at the scheduled time.</p>
      <p style="margin:24px 0;">
        <a href="{escape(meeting_url, quote=True)}" style="display:inline-block;background:#176b55;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:700;">
          Open meetings schedule
        </a>
      </p>
      <p style="color:#68758a;font-size:13px;line-height:1.5;">Sign in with your administrator account to access this meeting. This is an automated notification; please do not reply to this email.</p>
      <p style="color:#68758a;font-size:13px;margin-top:24px;">Regards,<br>{escape(school_name)} Team</p>
    </div>
    """
    sender_address = settings.DEFAULT_FROM_EMAIL
    if sender_address.endswith('@localhost') and settings.EMAIL_HOST_USER:
        sender_address = settings.EMAIL_HOST_USER
    from_email = f'{site.email_sender_name} <{sender_address}>'
    sent_count = 0
    for recipient in recipients:
        message = EmailMultiAlternatives(subject, text_body, from_email, [recipient])
        message.attach_alternative(html_body, 'text/html')
        try:
            sent_count += message.send(fail_silently=False)
        except (OSError, smtplib.SMTPException):
            logger.exception(
                'Failed to send student meeting notification for meeting %s to an admin.',
                meeting.pk,
            )
    return sent_count
