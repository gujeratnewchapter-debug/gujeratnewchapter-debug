from rest_framework import serializers
from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_number', 'course', 'course_title', 'student_name',
            'issued_at', 'pdf_file', 'verification_url',
        ]
        read_only_fields = fields
