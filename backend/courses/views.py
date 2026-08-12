from rest_framework import viewsets, permissions, filters, views
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Course, Section, Lesson
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    CourseWriteSerializer, SectionSerializer, LessonSerializer,
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
    search_fields = ['title', 'description']

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
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.section.course.instructor_id == request.user.id or request.user.is_super_admin


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
        return qs

    def perform_create(self, serializer):
        section = serializer.validated_data.get('section')
        if section and section.course.instructor_id != self.request.user.id and not self.request.user.is_super_admin:
            raise PermissionDenied("You can only add lessons to your own courses.")
        serializer.save()
