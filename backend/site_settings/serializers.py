from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import (
    Advertisement,
    AdvertisementEvent,
    SiteSettings,
    ContactMessage,
    HeroImage,
    PageContent,
    PageSection,
)


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']


class PageContentSerializer(serializers.ModelSerializer):
    sections = serializers.SerializerMethodField()

    def get_sections(self, obj):
        return PageSectionSerializer(obj.sections.filter(is_published=True), many=True, context=self.context).data

    class Meta:
        model = PageContent
        fields = ['slug', 'title', 'description', 'content', 'sections', 'is_published', 'updated_at']
        read_only_fields = ['updated_at']


class PageSectionSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(read_only=True)

    class Meta:
        model = PageSection
        fields = ['key', 'title', 'body', 'cta_url', 'cta_label', 'image', 'content', 'order']


class AdvertisementSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    video_file = serializers.SerializerMethodField()
    advertiser_logo = serializers.SerializerMethodField()

    class Meta:
        model = Advertisement
        fields = [
            'id', 'advertiser_name', 'content_type', 'headline', 'description',
            'promotional_text', 'image', 'image_url', 'image_alt_text', 'video_file',
            'video_url', 'advertiser_logo', 'cta_label', 'destination_url',
            'display_delay_seconds', 'close_countdown_seconds', 'frequency',
        ]

    def _media_url(self, file_field):
        if not file_field:
            return None
        url = file_field.url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request and url.startswith('/') else url

    def get_image(self, obj):
        return self._media_url(obj.image) or obj.image_url or None

    def get_video_file(self, obj):
        return self._media_url(obj.video_file)

    def get_advertiser_logo(self, obj):
        return self._media_url(obj.advertiser_logo)

    def validate(self, attrs):
        candidate = Advertisement(**{
            field.name: getattr(self.instance, field.name)
            for field in Advertisement._meta.fields
            if self.instance is not None
            and field.name not in ('id', 'created_at', 'updated_at')
        })
        for field, value in attrs.items():
            setattr(candidate, field, value)
        try:
            candidate.clean()
        except DjangoValidationError as error:
            if hasattr(error, 'message_dict'):
                raise serializers.ValidationError(error.message_dict) from error
            raise serializers.ValidationError(error.messages) from error
        return attrs


class AdvertisementEventSerializer(serializers.Serializer):
    advertisement_id = serializers.IntegerField(min_value=1)
    event_type = serializers.ChoiceField(choices=AdvertisementEvent.EventType.choices)
    event_id = serializers.UUIDField()


class HeroImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HeroImage
        fields = ['id', 'image']
        read_only_fields = ['id']


class SiteSettingsSerializer(serializers.ModelSerializer):
    hero_images = HeroImageSerializer(many=True, read_only=True)

    class Meta:
        model = SiteSettings
        fields = [
            'school_name', 'tagline', 'logo', 'address', 'phone', 'support_email',
            'bank_name', 'bank_account_name', 'bank_account_number', 'telebirr_number',
            'email_sender_name', 'email_verification_subject', 'hero_title', 'hero_subtitle',
            'hero_image', 'hero_images', 'hero_cta_label', 'hero_cta_url', 'social_links', 'updated_at',
        ]
        read_only_fields = ['updated_at']
