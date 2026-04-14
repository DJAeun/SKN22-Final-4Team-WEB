from rest_framework import serializers
from .models import Message, ChatMemory


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['message_id', 'user', 'sender_type', 'content', 'is_read', 'count', 'created_at']
        read_only_fields = ['message_id', 'count', 'created_at']


class ChatMemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMemory
        fields = ['memory_id', 'user', 'summary', 'keywords', 'ended_at']
        read_only_fields = ['memory_id']


class UserNameSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)


class UserPreferenceSerializer(serializers.Serializer):
    tone = serializers.ChoiceField(choices=['casual', 'formal'], required=False)
    title = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        allow_null=True,
    )

    def validate(self, attrs):
        if 'tone' not in attrs and 'title' not in attrs:
            raise serializers.ValidationError("Provide at least one of 'tone' or 'title'.")
        return attrs


class FrontendSignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    nickname = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, max_length=128)

    def validate_name(self, value):
        return value.strip()

    def validate_nickname(self, value):
        return value.strip()

    def validate_email(self, value):
        return value.strip().lower()
