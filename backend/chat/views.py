from django.shortcuts import render
from django.http import JsonResponse
import os
from rest_framework import viewsets, permissions
from .models import ChatSession, Message
from .serializers import ChatSessionSerializer, MessageSerializer

def chat_index(request):
    return render(request, 'chat/index.html')

class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(session__user=self.request.user)

    def perform_create(self, serializer):
        # We need to ensure the session belongs to the user
        session = serializer.validated_data['session']
        if session.user == self.request.user:
            serializer.save()
        else:
            raise PermissionError("You do not own this session.")

def debug_env(request):
    api_key = os.environ.get("OPENAI_API_KEY", "NOT_FOUND")
    # Mask most of the key for security
    masked_key = f"{api_key[:10]}..." if len(api_key) > 10 else api_key
    return JsonResponse({
        "OPENAI_API_KEY_LOADED": api_key != "NOT_FOUND",
        "KEY_PREVIEW": masked_key,
        "REDIS_HOST": os.environ.get("REDIS_HOST", "localhost (default)")
    })
