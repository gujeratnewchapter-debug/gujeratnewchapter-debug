import io
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
import qrcode

from .models import Certificate
from .serializers import CertificateSerializer
from enrollments.models import Enrollment


def generate_certificate_pdf(certificate):
    """Render a simple certificate PDF with an embedded QR verification code."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)

    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(width / 2, height - 120, "Certificate of Completion")

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 180, f"This certifies that")

    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width / 2, height - 215, certificate.student.get_full_name() or certificate.student.username)

    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 250, "has successfully completed the course")

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 285, certificate.course.title)

    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 320, f"Certificate No: {certificate.certificate_number}")
    c.drawCentredString(width / 2, height - 340, f"Issued: {certificate.issued_at.strftime('%B %d, %Y')}")

    # QR code for verification
    qr_data = certificate.verification_url or str(certificate.certificate_number)
    qr_img = qrcode.make(qr_data)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    from reportlab.lib.utils import ImageReader
    c.drawImage(ImageReader(qr_buffer), width - 150, 40, width=90, height=90)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(student=self.request.user)

    @action(detail=False, methods=['post'])
    def issue(self, request):
        """Issue a certificate once a course enrollment reaches 100% progress."""
        course_id = request.data.get('course_id')
        enrollment = Enrollment.objects.filter(student=request.user, course_id=course_id).first()
        if not enrollment or enrollment.progress_percent < 100:
            raise PermissionDenied("Course not yet completed.")

        certificate, created = Certificate.objects.get_or_create(
            student=request.user, course=enrollment.course,
        )
        if created or not certificate.pdf_file:
            certificate.verification_url = f"https://yourdomain.com/verify/{certificate.certificate_number}/"
            pdf_buffer = generate_certificate_pdf(certificate)
            certificate.pdf_file.save(
                f"certificate_{certificate.certificate_number}.pdf",
                ContentFile(pdf_buffer.read()),
                save=True,
            )
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
