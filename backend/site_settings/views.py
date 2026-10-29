from django.db import IntegrityError, models, transaction
from django.utils import timezone
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Advertisement, AdvertisementEvent, SiteSettings, ContactMessage, PageContent
from .serializers import (
    AdvertisementEventSerializer,
    AdvertisementSerializer,
    SiteSettingsSerializer,
    ContactMessageSerializer,
    PageContentSerializer,
)


class SiteSettingsView(APIView):
    """
    GET is public (navbar/footer/branding on every page read this).
    PATCH is admin-only (lets admins edit footer/contact/bank info
    without touching code, per the request).
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        # Pass `request` into serializer context so ImageFields produce absolute URLs
        return Response(SiteSettingsSerializer(SiteSettings.load(), context={'request': request}).data)

    def patch(self, request):
        if not (request.user.is_super_admin):
            return Response({"detail": "Admin only."}, status=403)
        settings_obj = SiteSettings.load()
        serializer = SiteSettingsSerializer(settings_obj, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ContactMessageView(APIView):
    """Public endpoint the footer 'Contact Us' form submits to."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Message received."}, status=201)


class PageContentView(APIView):
    """Public read endpoint for admin-managed page copy."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug):
        page = PageContent.objects.filter(slug=slug, is_published=True).first()
        if page is None and slug == 'home':
            page, _ = PageContent.objects.get_or_create(
                slug='home',
                defaults={
                    'title': 'Ethiopian Startup School',
                    'description': 'Learn entrepreneurship, AI, and business skills with practical guidance.',
                    'is_published': True,
                },
            )
        if page is None:
            return Response({'detail': 'Page content not found.'}, status=404)
        return Response(PageContentSerializer(page, context={'request': request}).data)


class AdvertisementListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not SiteSettings.load().advertisements_enabled:
            return Response([])
        route = request.query_params.get('path', '/')
        if not route.startswith('/') or route.startswith('//') or '?' in route or '#' in route:
            return Response({'detail': 'Provide a valid route path.'}, status=status.HTTP_400_BAD_REQUEST)
        advertisements = Advertisement.active_for_route(route, now=timezone.now())
        data = AdvertisementSerializer(
            advertisements,
            many=True,
            context={'request': request},
        ).data
        return Response(data)


class AdvertisementEventView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = AdvertisementEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        advertisement = Advertisement.objects.filter(
            pk=values['advertisement_id'],
            is_active=True,
        ).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=timezone.now()),
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=timezone.now()),
        ).first()
        if advertisement is None or not SiteSettings.load().advertisements_enabled:
            return Response({'detail': 'Advertisement is not active.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                event, created = AdvertisementEvent.objects.get_or_create(
                    event_id=values['event_id'],
                    defaults={
                        'advertisement': advertisement,
                        'event_type': values['event_type'],
                    },
                )
        except IntegrityError:
            event = AdvertisementEvent.objects.filter(event_id=values['event_id']).first()
            created = False

        if event is None:
            return Response({'detail': 'Unable to record advertisement event.'}, status=500)
        if not created and (
            event.advertisement_id != advertisement.id
            or event.event_type != values['event_type']
        ):
            return Response({'detail': 'Event identifier has already been used.'}, status=409)
        return Response({'tracked': created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
