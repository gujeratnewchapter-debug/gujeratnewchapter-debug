from django.db.models import Count
from django.db.models.functions import TruncMonth
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import ServiceRequest, VisitorEvent, PlatformStat
from .serializers import ServiceRequestSerializer, VisitorEventSerializer, PlatformStatSerializer


class ServiceRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ServiceRequestSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'is_super_admin', False):
            return ServiceRequest.objects.all()
        return ServiceRequest.objects.filter(requester=user)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(
                requester=self.request.user,
                name=self.request.user.get_full_name(),
                email=self.request.user.email,
            )
        else:
            serializer.save()


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def record_visitor(request):
    serializer = VisitorEventSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({'recorded': True}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def analytics_summary(request):
    monthly = VisitorEvent.objects.annotate(month=TruncMonth('created_at')).values('month').annotate(visitors=Count('session_key', distinct=True)).order_by('month')
    return Response({'visitors': VisitorEvent.objects.values('session_key').distinct().count(), 'events': VisitorEvent.objects.count(), 'monthly': list(monthly), 'service_requests': ServiceRequest.objects.count()})


def live_stat_value(metric):
    from accounts.models import User
    from certificates.models import Certificate
    from courses.models import Course
    from enrollments.models import Enrollment
    sources = {
        PlatformStat.Metric.COURSES: Course.objects.filter(status=Course.Status.PUBLISHED).count,
        PlatformStat.Metric.STUDENTS: lambda: User.objects.filter(role=User.Role.STUDENT).count(),
        PlatformStat.Metric.INSTRUCTORS: lambda: User.objects.filter(role=User.Role.INSTRUCTOR).count(),
        PlatformStat.Metric.VISITORS: lambda: VisitorEvent.objects.exclude(session_key='').values('session_key').distinct().count(),
        PlatformStat.Metric.CERTIFICATES: Certificate.objects.count,
        PlatformStat.Metric.SERVICE_REQUESTS: ServiceRequest.objects.count,
    }
    return sources.get(metric, lambda: None)()


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def platform_stats(request):
    stats = []
    for item in PlatformStat.objects.filter(is_enabled=True):
        value = item.manual_value if item.manual_value is not None else live_stat_value(item.metric)
        if value is not None:
            stats.append({'metric': item.metric, 'label': item.label, 'translations': item.translations, 'value': value})
    return Response(stats)