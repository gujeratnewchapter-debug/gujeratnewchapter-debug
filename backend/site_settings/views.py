from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import SiteSettings, ContactMessage, PageContent
from .serializers import SiteSettingsSerializer, ContactMessageSerializer, PageContentSerializer


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
