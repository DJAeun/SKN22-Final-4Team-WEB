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
