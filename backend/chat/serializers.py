from rest_framework import serializers
from .models import ChatSession, Message
from django.contrib.auth import get_user_model

User = get_user_model()

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'session', 'sender', 'text', 'created_at', 'emotion_state']
        read_only_fields = ['id', 'created_at', 'emotion_state']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatSession
        fields = ['id', 'user', 'started_at', 'updated_at', 'summary', 'messages']
        read_only_fields = ['id', 'user', 'started_at', 'updated_at', 'summary']
