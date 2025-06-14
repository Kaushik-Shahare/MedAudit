from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from .models import UserProfile

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['name', 'location', 'phone_number', 'email', 'user_type']

    def get_email(self, obj):
        return obj.user.email

    def get_user_type(self, obj):
        return obj.user.user_type.name if obj.user.user_type else None

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['name', 'location', 'phone_number']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    user_type = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'password', 'user_type')

    def create(self, validated_data):
        user_type = validated_data.pop('user_type', None)
        user = User.objects.create_user(user_type=user_type, **validated_data)
        user.user_stage = 1  # After registration, stage is 1 (profile incomplete)
        user.save()
        # UserProfile will be created by the signal
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if user and user.is_active:
            return user
        raise serializers.ValidationError('Invalid credentials')

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField() 