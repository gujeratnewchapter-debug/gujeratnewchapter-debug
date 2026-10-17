from rest_framework import serializers

from .models import Article, Notice


class ArticleSerializer(serializers.ModelSerializer):
    featured_image = serializers.ImageField()
    is_featured = serializers.BooleanField(default=True)

    class Meta:
        model = Article
        fields = [
            'id',
            'title',
            'slug',
            'short_description',
            'content',
            'featured_image',
            'image_alt_text',
            'category',
            'author',
            'published_at',
            'is_published',
            'is_featured',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NoticeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notice
        fields = [
            'id',
            'title',
            'slug',
            'body',
            'is_published',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
