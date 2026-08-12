from rest_framework import serializers
from .models import SiteSettings, ContactMessage, HeroImage


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']


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
