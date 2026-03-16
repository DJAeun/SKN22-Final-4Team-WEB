from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True, null=True, help_text="Summary of the conversation for context injection")

    def __str__(self):
        return f"Session {self.id} - {self.user.username}"

class Message(models.Model):
    SENDER_CHOICES = [
        ('user', 'User'),
        ('hari', 'Ha-ri'),
    ]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    emotion_state = models.JSONField(blank=True, null=True, help_text="Stored LLM evaluation of emotion/context")

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.get_sender_display()}] {self.text[:30]}"
