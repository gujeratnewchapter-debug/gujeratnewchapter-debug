from rest_framework import permissions, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from .models import Article
from .serializers import ArticleSerializer


class ArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        articles = Article.objects.all()
        if not self.request.user.is_staff:
            articles = articles.filter(is_published=True)
        if self.request.query_params.get('featured', '').lower() == 'true':
            articles = articles.filter(is_published=True, is_featured=True)
        return articles.order_by('-published_at', '-created_at')

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
