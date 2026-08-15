from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_field = self.username_field
        username = attrs.get(username_field)
        password = attrs.get('password')

        if username and '@' in username:
            try:
                user = User.objects.get(email__iexact=username)
                attrs[username_field] = user.get_username()
            except User.DoesNotExist:
                pass

        return super().validate(attrs)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone_number', 'bio', 'avatar', 'is_email_verified',
            'created_at',
        ]
        read_only_fields = ['id', 'is_email_verified', 'created_at']


class RegisterSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=False, allow_blank=True)
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'full_name', 'first_name', 'last_name', 'role']
        read_only_fields = ['id']

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
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
