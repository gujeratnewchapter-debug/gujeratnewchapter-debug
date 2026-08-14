from django.db import models
from django.conf import settings


class Category(models.Model):
    """RFP section 8: Course Categories (Startup, Innovation, Business, etc.)"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Course(models.Model):
    class Level(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    subtitle = models.CharField(max_length=500, blank=True)
    description = models.TextField(help_text="Rich text/HTML from the course-builder editor")
    short_description = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True, help_text="Rich text course notes shown to students")
    notes_enabled = models.BooleanField(default=False, help_text="Toggle: show the notes card to students")
    learning_objectives = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    target_audience = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='courses_taught')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_free = models.BooleanField(default=False)
    language = models.CharField(max_length=50, default='English')
    duration_hours = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def total_lessons(self):
        return Lesson.objects.filter(section__course=self).count()

    def ordered_lessons(self):
        """Flattened lesson sequence across all sections, in display order.
        Used to determine 'the next lesson' and 'the previous lesson' for
        the quiz pass-to-unlock gate."""
        return list(
            Lesson.objects.filter(section__course=self)
            .select_related('section')
            .order_by('section__order', 'order')
        )


class Section(models.Model):
    """Course -> Section -> Lesson structure (RFP section 8)."""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lesson(models.Model):
    class LessonType(models.TextChoices):
        VIDEO = 'video', 'Video'
        PDF = 'pdf', 'PDF'
        POWERPOINT = 'powerpoint', 'PowerPoint'
        TEXT = 'text', 'Text'
        INTERACTIVE_HTML = 'interactive_html', 'Interactive HTML'
        CODING_EXERCISE = 'coding_exercise', 'Coding Exercise'
        AUDIO = 'audio', 'Audio'
        LIVE_SESSION = 'live_session', 'Live Session'

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    lesson_type = models.CharField(max_length=30, choices=LessonType.choices, default=LessonType.VIDEO)
    order = models.PositiveIntegerField(default=0)
    content_text = models.TextField(blank=True, help_text="Rich text/HTML for text/interactive HTML lessons")
    video_url = models.URLField(blank=True, help_text="YouTube/Vimeo embed or S3/R2/MinIO URL")
    source_url = models.URLField(blank=True, help_text="Pasted external URL for PDF/slides/other hosted files")
    file = models.FileField(upload_to='lesson_files/', blank=True, null=True, help_text="Directly uploaded PDF/PPTX/audio file")
    duration_minutes = models.PositiveIntegerField(default=0)
    is_preview = models.BooleanField(default=False, help_text="Free preview lesson for guests")
    is_downloadable = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.section.course.title} - {self.title}"


class Resource(models.Model):
    """Extra downloadable resources attached to a lesson."""
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='resources/')

    def __str__(self):
        return self.title
