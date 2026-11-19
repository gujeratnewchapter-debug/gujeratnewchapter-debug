import unicodedata

from rest_framework import serializers

from .models import SupportCallRequest


def _reject_control_characters(value):
    if any(unicodedata.category(character) == 'Cc' for character in value):
        raise serializers.ValidationError('Control characters are not allowed.')
    return value


class SupportCallCreateSerializer(serializers.Serializer):
    display_name = serializers.CharField(min_length=2, max_length=100, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    question = serializers.CharField(max_length=500, required=False, allow_blank=True, trim_whitespace=True)
    mode = serializers.ChoiceField(choices=SupportCallRequest.Mode.choices)

    def validate_display_name(self, value):
        return _reject_control_characters(value)

    def validate_question(self, value):
        return _reject_control_characters(value)


class SupportCallCapabilitySerializer(serializers.Serializer):
    call_id = serializers.UUIDField()
    capability = serializers.CharField(min_length=32, max_length=128, trim_whitespace=False)


class SupportCallAdminOutboundSerializer(serializers.Serializer):
    student_id = serializers.IntegerField(min_value=1)
    mode = serializers.ChoiceField(choices=SupportCallRequest.Mode.choices)


class SupportCallAdminSerializer(serializers.ModelSerializer):
    call_id = serializers.UUIDField(source='id', read_only=True)
    mode_label = serializers.CharField(source='get_mode_display', read_only=True)
    recipient_id = serializers.IntegerField(read_only=True, allow_null=True)
    direction_label = serializers.CharField(source='get_direction_display', read_only=True)

    class Meta:
        model = SupportCallRequest
        fields = (
            'call_id',
            'display_name',
            'email',
            'question',
            'mode',
            'mode_label',
            'direction',
            'direction_label',
            'recipient_id',
            'status',
            'created_at',
            'accepted_at',
            'expires_at',
        )


class SupportCallStudentSerializer(serializers.ModelSerializer):
    call_id = serializers.UUIDField(source='id', read_only=True)
    mode_label = serializers.CharField(source='get_mode_display', read_only=True)
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = SupportCallRequest
        fields = (
            'call_id',
            'display_name',
            'question',
            'mode',
            'mode_label',
            'accepted_at',
            'status',
            'created_at',
            'expires_at',
        )

    def get_display_name(self, call):
        admin = call.handled_by
        if admin is None:
            return 'ESS administrator'
        return (admin.get_full_name() or admin.username).strip()
