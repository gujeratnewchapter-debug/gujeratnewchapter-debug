from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_field = self.username_field
        username = attrs.get(username_field)
        password = attrs.get('password')

        if username and '@' in username:
            email_users = list(User.objects.filter(email__iexact=username).order_by('pk'))
            if len(email_users) == 1:
                attrs[username_field] = email_users[0].get_username()
            elif len(email_users) > 1:
                matching_users = [
                    user for user in email_users
                    if user.is_active and user.check_password(attrs.get('password', ''))
                ]
                if len(matching_users) != 1:
                    raise AuthenticationFailed(
                        self.error_messages['no_active_account'],
                        code='no_active_account',
                    )
                attrs[username_field] = matching_users[0].get_username()

        return super().validate(attrs)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)


class UserSerializer(serializers.ModelSerializer):
    is_super_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone_number', 'bio', 'avatar', 'is_email_verified',
            'is_super_admin', 'created_at',
        ]
        read_only_fields = ['id', 'role', 'is_email_verified', 'created_at']

    def validate_avatar(self, value):
        request = self.context.get('request')
        if self.instance and self.instance.is_instructor and request and request.user == self.instance:
            raise serializers.ValidationError('Instructor photos are managed by an administrator.')
        return value


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'full_name', 'first_name', 'last_name', 'role']
        read_only_fields = ['id', 'role']

    def validate(self, attrs):
        email = (attrs.get('email') or '').strip()
        if email:
            attrs['email'] = email.lower()

        full_name = (attrs.get('full_name') or '').strip()
        first_name = (attrs.get('first_name') or '').strip()
        last_name = (attrs.get('last_name') or '').strip()

        if full_name and not first_name and not last_name:
            parts = full_name.split()
            if parts:
                attrs['first_name'] = parts[0]
                attrs['last_name'] = ' '.join(parts[1:])
        elif full_name:
            if not first_name:
                attrs['first_name'] = full_name.split()[0]
            if not last_name:
                attrs['last_name'] = ' '.join(full_name.split()[1:])

        username = (attrs.get('username') or '').strip()
        if not username and email:
            base = email.split('@')[0].lower()
            candidate = base
            index = 1
            while User.objects.filter(username=candidate).exists():
                index += 1
                candidate = f"{base}{index}"
            attrs['username'] = candidate

        return super().validate(attrs)

    def validate_role(self, value):
        # Guests self-registering can only become students or instructors, never super_admin
        if value == User.Role.SUPER_ADMIN:
            raise serializers.ValidationError("Cannot self-register as super admin.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('full_name', None)
        validated_data['role'] = User.Role.STUDENT
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
