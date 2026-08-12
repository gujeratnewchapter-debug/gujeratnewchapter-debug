from django.db import models
from django.conf import settings
from courses.models import Course, Lesson


class Conversation(models.Model):
    """One AI Tutor/Mentor chat thread per student (RFP section 9)."""
    class Mode(models.TextChoices):
        TUTOR = 'tutor', 'AI Tutor'
        MENTOR = 'mentor', 'AI Startup Mentor'
        COACH = 'coach', 'AI Business Coach'

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_conversations')
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True)
    mode = models.CharField(max_length=20, choices=Mode.choices, default=Mode.TUTOR)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student} - {self.mode} - {self.title}"


class Message(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    # RAG: which knowledge-base sources were cited in this assistant reply (section 10)
    sources = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class KnowledgeDocument(models.Model):
    """
    Approved knowledge-base source for RAG (RFP section 10).
    Text is chunked+embedded by a background task; embeddings live in a
    vector store (e.g. pgvector/Chroma/Pinecone) referenced by `vector_ref`.
    """
    class SourceType(models.TextChoices):
        PDF = 'pdf', 'PDF'
        DOCX = 'docx', 'DOCX'
        VIDEO_TRANSCRIPT = 'video_transcript', 'Video Transcript'
        POLICY = 'policy', 'Policy'
        STARTUP_MANUAL = 'startup_manual', 'Startup Manual'
        GOV_GUIDELINE = 'gov_guideline', 'Government Guideline'
        COURSE_MATERIAL = 'course_material', 'Course Material'

    title = models.CharField(max_length=255)
    source_type = models.CharField(max_length=30, choices=SourceType.choices)
    course = models.ForeignKey(Course, on_delete=models.SET_NULL, null=True, blank=True, related_name='knowledge_docs')
    file = models.FileField(upload_to='knowledge_base/', blank=True, null=True)
    raw_text = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    is_indexed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (v{self.version})"
