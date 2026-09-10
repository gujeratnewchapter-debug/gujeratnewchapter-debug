import io
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image, ImageFilter

from .models import Certificate
from .serializers import CertificateSerializer
from enrollments.models import Enrollment


def get_watermark_path():
    configured_path = Path(settings.MEDIA_ROOT) / 'certificates' / 'certificate-watermark.png'
    if configured_path.exists():
        return configured_path

    try:
        from site_settings.models import SiteSettings
        hero_image = SiteSettings.load().hero_image
        if hero_image and hero_image.path and Path(hero_image.path).exists():
            return Path(hero_image.path)
    except (OSError, ValueError):
        pass

    return None


def generate_certificate_pdf(certificate):
    """Render a formal branded certificate PDF with QR verification."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    navy = colors.HexColor('#123B5D')
    teal = colors.HexColor('#0F766E')
    mint = colors.HexColor('#DDF4EE')
    ink = colors.HexColor('#263640')
    muted = colors.HexColor('#65747C')
    gold = colors.HexColor('#D5A84A')

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)

    watermark_path = get_watermark_path()
    if watermark_path and watermark_path.exists():
        watermark = Image.open(watermark_path).convert('RGBA')
        watermark.thumbnail((int(width * 0.82), int(height * 0.82)), Image.Resampling.LANCZOS)
        watermark = watermark.filter(ImageFilter.GaussianBlur(radius=1.2))
        alpha = watermark.getchannel('A').point(lambda value: int(value * 0.13))
        watermark.putalpha(alpha)
        watermark_buffer = io.BytesIO()
        watermark.save(watermark_buffer, format='PNG')
        watermark_buffer.seek(0)
        watermark_width, watermark_height = watermark.size
        watermark_x = (width - watermark_width) / 2
        watermark_y = (height - watermark_height) / 2
        c.drawImage(
            ImageReader(watermark_buffer),
            watermark_x,
            watermark_y,
            width=watermark_width,
            height=watermark_height,
            mask='auto',
        )

    c.setStrokeColor(navy)
    c.setLineWidth(3)
    c.rect(22, 22, width - 44, height - 44, fill=0, stroke=1)
    c.setStrokeColor(teal)
    c.setLineWidth(1)
    c.rect(31, 31, width - 62, height - 62, fill=0, stroke=1)

    # Branded top band and wordmark.
    c.setFillColor(navy)
    c.rect(32, height - 86, width - 64, 54, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 17)
    c.drawString(55, height - 64, 'ETHIOPIAN STARTUP SCHOOL')
    c.setFont('Helvetica', 8)
    c.setFillColor(mint)
    c.drawString(56, height - 77, 'ENTREPRENEURSHIP EDUCATION AND INNOVATION')
    c.setFont('Helvetica-Bold', 8)
    c.setFillColor(colors.white)
    c.drawRightString(width - 55, height - 64, 'LEARN  |  BUILD  |  GROW')

    # Formal seal.
    seal_x, seal_y = 80, height - 151
    c.setStrokeColor(gold)
    c.setLineWidth(2)
    c.circle(seal_x, seal_y, 27, fill=0, stroke=1)
    c.setFillColor(teal)
    c.circle(seal_x, seal_y, 21, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont('Helvetica-Bold', 10)
    c.drawCentredString(seal_x, seal_y + 3, 'ESS')
    c.setFont('Helvetica', 5)
    c.drawCentredString(seal_x, seal_y - 8, 'VERIFIED')

    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 25)
    c.drawCentredString(width / 2, height - 137, 'CERTIFICATE OF COMPLETION')
    c.setFillColor(teal)
    c.setFont('Helvetica-Bold', 8)
    c.drawCentredString(width / 2, height - 153, 'STARTUP FUNDAMENTALS PROGRAM')
    c.setFillColor(muted)
    c.setFont('Helvetica', 12)
    c.drawCentredString(width / 2, height - 185, 'This certificate is proudly presented to')

    student_name = certificate.student.get_full_name() or certificate.student.username
    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 27)
    c.drawCentredString(width / 2, height - 224, student_name)
    name_width = min(stringWidth(student_name, 'Helvetica-Bold', 27) + 30, width - 180)
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.line((width - name_width) / 2, height - 235, (width + name_width) / 2, height - 235)

    c.setFillColor(ink)
    c.setFont('Helvetica', 12)
    c.drawCentredString(width / 2, height - 263, 'for successfully completing')
    c.setFillColor(teal)
    c.setFont('Helvetica-Bold', 19)
    course_title = certificate.course.title
    if len(course_title) > 68:
        split_at = course_title.rfind(' ', 0, 68)
        c.drawCentredString(width / 2, height - 291, course_title[:split_at])
        c.drawCentredString(width / 2, height - 313, course_title[split_at + 1:])
    else:
        c.drawCentredString(width / 2, height - 302, course_title)

    # Metadata strip.
    strip_y = 82
    c.setFillColor(mint)
    c.roundRect(116, strip_y, width - 232, 45, 6, fill=1, stroke=0)
    minutes, seconds = divmod(certificate.time_taken_seconds or 0, 60)
    metadata = [
        ('ISSUED', certificate.issued_at.strftime('%B %d, %Y')),
        ('FINAL EXAM', f'{minutes}m {seconds:02d}s'),
        ('CERTIFICATE NO.', str(certificate.certificate_number)[:18]),
    ]
    column_width = (width - 232) / 3
    for index, (label, value) in enumerate(metadata):
        center_x = 116 + column_width * index + column_width / 2
        c.setFillColor(teal)
        c.setFont('Helvetica-Bold', 7)
        c.drawCentredString(center_x, strip_y + 29, label)
        c.setFillColor(ink)
        c.setFont('Helvetica', 9)
        c.drawCentredString(center_x, strip_y + 14, value)

    c.setStrokeColor(muted)
    c.setLineWidth(.8)
    c.line(60, 57, 190, 57)
    c.line(width - 190, 57, width - 60, 57)
    c.setFillColor(muted)
    c.setFont('Helvetica', 8)
    c.drawCentredString(125, 43, 'PROGRAM DIRECTOR')
    c.drawCentredString(width - 125, 43, 'DIGITAL VERIFICATION')

    # QR code for verification.
    qr_data = certificate.verification_url or str(certificate.certificate_number)
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    c.drawImage(ImageReader(qr_buffer), width - 105, 39, width=58, height=58)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def ensure_certificate(student, course, time_taken_seconds=0):
    certificate, created = Certificate.objects.get_or_create(student=student, course=course)
    certificate.time_taken_seconds = time_taken_seconds or certificate.time_taken_seconds or 0
    certificate.verification_url = f"{settings.FRONTEND_BASE_URL}/verify-certificate/{certificate.certificate_number}"
    if created or not certificate.pdf_file or not certificate.verification_url or get_watermark_path():
        pdf_buffer = generate_certificate_pdf(certificate)
        certificate.pdf_file.save(
            f"certificate_{certificate.certificate_number}.pdf",
            ContentFile(pdf_buffer.read()),
            save=False,
        )
    certificate.save()
    return certificate


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from enrollments.models import Enrollment
        completed_enrollments = Enrollment.objects.filter(
            student=self.request.user,
            progress_percent__gte=100,
        ).select_related('course')
        for enrollment in completed_enrollments:
            ensure_certificate(self.request.user, enrollment.course)
        return Certificate.objects.filter(student=self.request.user)

    @action(detail=False, methods=['post'])
    def issue(self, request):
        """Issue a certificate once a course enrollment reaches 100% progress."""
        course_id = request.data.get('course_id')
        enrollment = Enrollment.objects.filter(student=request.user, course_id=course_id).first()
        if not enrollment or enrollment.progress_percent < 100:
            raise PermissionDenied("Course not yet completed.")

        certificate = ensure_certificate(request.user, enrollment.course)
        return Response(CertificateSerializer(certificate).data)


class VerifyCertificateView(viewsets.ViewSet):
    """Public certificate verification endpoint (RFP section 15: QR verification)."""
    permission_classes = [permissions.AllowAny]

    def retrieve(self, request, pk=None):
        try:
            certificate = Certificate.objects.get(certificate_number=pk)
        except Certificate.DoesNotExist:
            return Response({'valid': False}, status=404)
        return Response({'valid': True, **CertificateSerializer(certificate).data})
