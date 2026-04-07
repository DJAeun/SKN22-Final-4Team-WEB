from rest_framework import serializers
from .models import RpgSession, RpgChatLog

class RpgSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RpgSession
        fields = ['id', 'user', 'user_nickname', 'total_tokens', 'status_window_enabled', 'stress', 'crack_stage', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'total_tokens', 'stress', 'crack_stage', 'created_at', 'updated_at']

class RpgChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RpgChatLog
        fields = ['id', 'session', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'session', 'role', 'content', 'created_at']
