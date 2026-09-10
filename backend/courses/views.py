from rest_framework.decorators import action
from rest_framework import viewsets, permissions, filters, views
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Course, Section, Lesson, Resource
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    CourseWriteSerializer, SectionSerializer, LessonSerializer,
    ResourceSerializer,
)


class IsInstructorOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.instructor_id == request.user.id or request.user.is_super_admin


class IsResourceCourseInstructorOrReadOnly(permissions.BasePermission):
    """Resources may be mutated only by the owning course instructor/admin."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.lesson.section.course.instructor_id == request.user.id or request.user.is_super_admin


class GlobalSearchView(views.APIView):
    """
    Sitewide course-search used by the navbar search box. Searches published
    course titles/descriptions and lesson titles, returning course results
    (a matching lesson surfaces its parent course so students land on
    something enrollable).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'results': []})

        from django.db.models import Q
        course_matches = Course.objects.filter(
            Q(status=Course.Status.PUBLISHED),
            Q(title__icontains=query) | Q(description__icontains=query) | Q(short_description__icontains=query),
        ).select_related('instructor', 'category')[:10]

        lesson_matches = Course.objects.filter(
            status=Course.Status.PUBLISHED,
            sections__lessons__title__icontains=query,
        ).select_related('instructor', 'category').distinct()[:10]

        combined = {c.id: c for c in course_matches}
        for c in lesson_matches:
            combined[c.id] = c

        serializer = CourseListSerializer(list(combined.values()), many=True, context={'request': request})
        return Response({'results': serializer.data})


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class CourseViewSet(viewsets.ModelViewSet):
    """
    Guests/students: browse published courses (RFP section 5 Guest, Student).
    Instructors: full CRUD on their own courses (RFP section 11 Course Builder).
    """
    queryset = Course.objects.select_related('instructor', 'category').all()
    permission_classes = [IsInstructorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'level', 'is_free', 'status', 'instructor']
    search_fields = ['slug', 'title', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return CourseWriteSerializer
        return CourseDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated or user.is_student:
            # Guests & students only see published courses
            qs = qs.filter(status=Course.Status.PUBLISHED)
        elif user.is_instructor:
            # Instructors see their own courses at every status, plus published ones
            from django.db.models import Q
            qs = qs.filter(Q(status=Course.Status.PUBLISHED) | Q(instructor=user))
        return qs

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    @action(detail=False, methods=['get'], url_path='instructor-analytics')
    def instructor_analytics(self, request):
        """Return enrollment, engagement, completion, and certificate metrics for owned courses."""
        if not request.user.is_authenticated or not (request.user.is_instructor or request.user.is_super_admin):
            return Response({'detail': 'Instructor access required.'}, status=403)

        from certificates.models import Certificate
        from enrollments.models import Enrollment, LessonProgress

        owned_courses = Course.objects.all() if request.user.is_super_admin else Course.objects.filter(instructor=request.user)
        enrollments = Enrollment.objects.filter(course__in=owned_courses)
        progress = LessonProgress.objects.filter(enrollment__in=enrollments)
        course_rows = []
        for course in owned_courses.order_by('-created_at'):
            course_enrollments = enrollments.filter(course=course)
            course_progress = progress.filter(enrollment__course=course)
            registered = course_enrollments.count()
            attending = course_enrollments.filter(progress_percent__gt=0).count()
            completed = course_enrollments.filter(completed_at__isnull=False).count()
            certificates = Certificate.objects.filter(course=course).count()
            course_rows.append({
                'course_id': course.id,
                'title': course.title,
                'status': course.status,
                'registered_students': registered,
                'attending_students': attending,
                'active_students': attending,
                'completed_students': completed,
                'certificates_issued': certificates,
                'lesson_completions': course_progress.filter(is_completed=True).count(),
                'average_progress_percent': round(sum(item.progress_percent for item in course_enrollments) / registered) if registered else 0,
            })

        return Response({
            'totals': {
                'courses': owned_courses.count(),
                'registered_students': enrollments.count(),
                'attending_students': enrollments.filter(progress_percent__gt=0).count(),
                'completed_students': enrollments.filter(completed_at__isnull=False).count(),
                'certificates_issued': Certificate.objects.filter(course__in=owned_courses).count(),
            },
            'courses': course_rows,
        })


class IsCourseInstructorOrReadOnly(permissions.BasePermission):
    """For Section objects — ownership lives on the parent Course, not the Section itself."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.course.instructor_id == request.user.id or request.user.is_super_admin


class IsLessonCourseInstructorOrReadOnly(permissions.BasePermission):
    """For Lesson objects — ownership lives on section.course, two hops up."""
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and (request.user.is_instructor or request.user.is_super_admin)

    def has_object_permission(self, request, view, obj):
        if request.user.is_authenticated and (request.user.is_super_admin or obj.section.course.instructor_id == request.user.id):
            return True
        if request.method in permissions.SAFE_METHODS and obj.is_preview:
            return True
        if request.method not in permissions.SAFE_METHODS or not request.user.is_authenticated:
            return False
        from enrollments.models import Enrollment, is_lesson_unlocked
        if not Enrollment.objects.filter(student=request.user, course=obj.section.course).exists():
            return False
        return is_lesson_unlocked(request.user, obj)


class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsCourseInstructorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        course_id = self.request.query_params.get('course')
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def perform_create(self, serializer):
        course = serializer.validated_data.get('course')
        if course and course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add sections to your own courses.")
        serializer.save()


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsLessonCourseInstructorOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        section_id = self.request.query_params.get('section')
        if section_id:
            qs = qs.filter(section_id=section_id)
        user = self.request.user
        if user.is_authenticated and (user.is_super_admin or user.is_instructor):
            if user.is_super_admin:
                return qs
            return qs.filter(section__course__instructor=user)

        if not user.is_authenticated:
            return qs.filter(is_preview=True)

        from enrollments.models import Enrollment, is_lesson_unlocked
        candidate_lessons = qs.filter(
            Q(is_preview=True) |
            Q(section__course__enrollments__student=user)
        ).select_related('section__course').distinct()
        accessible_ids = [
            lesson.id for lesson in candidate_lessons
            if lesson.is_preview or is_lesson_unlocked(user, lesson)
        ]
        return qs.filter(id__in=accessible_ids)

    def perform_create(self, serializer):
        section = serializer.validated_data.get('section')
        if section and section.course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add lessons to your own courses.")
        serializer.save()


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.select_related('lesson__section__course').all()
    serializer_class = ResourceSerializer
    permission_classes = [IsResourceCourseInstructorOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        lesson_id = self.request.query_params.get('lesson')
        if lesson_id:
            queryset = queryset.filter(lesson_id=lesson_id)
        user = self.request.user
        if user.is_authenticated and user.is_super_admin:
            return queryset
        if user.is_authenticated and user.is_instructor:
            return queryset.filter(lesson__section__course__instructor=user)
        if not user.is_authenticated:
            return queryset.filter(lesson__is_preview=True)

        from enrollments.models import Enrollment, is_lesson_unlocked
        candidate_resources = queryset.filter(
            Q(lesson__is_preview=True) |
            Q(lesson__section__course__enrollments__student=user)
        ).select_related('lesson__section__course').distinct()
        accessible_ids = [
            resource.id for resource in candidate_resources
            if resource.lesson.is_preview or (
                Enrollment.objects.filter(
                    student=user, course=resource.lesson.section.course,
                ).exists() and is_lesson_unlocked(user, resource.lesson)
            )
        ]
        return queryset.filter(id__in=accessible_ids)

    def perform_create(self, serializer):
        lesson = serializer.validated_data['lesson']
        if lesson.section.course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied('You can only add resources to your own lessons.')
        serializer.save()

    @action(detail=False, methods=['post'], url_path='replace-videos')
    def replace_videos(self, request):
        lesson_id = request.data.get('lesson')
        lesson = Lesson.objects.filter(id=lesson_id).select_related('section__course').first()
        if not lesson:
            return Response({'detail': 'Lesson not found.'}, status=404)
        if lesson.section.course.instructor_id != request.user.id and not request.user.is_super_admin:
            raise PermissionDenied('You can only edit resources in your own lessons.')

        Resource.objects.filter(lesson=lesson, resource_type=Resource.ResourceType.VIDEO).delete()
        resources = []
        for index, video_url in enumerate(request.data.get('urls', [])):
            if video_url:
                resources.append(Resource(
                    lesson=lesson,
                    title=f'{lesson.title} video {index + 1}',
                    resource_type=Resource.ResourceType.VIDEO,
                    url=video_url,
                    order=index + 1,
                ))
        Resource.objects.bulk_create(resources)
        return Response(ResourceSerializer(resources, many=True, context={'request': request}).data)
