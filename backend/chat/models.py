from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True)
    # session_key = models.CharField(max_length=64, null=True, blank=True, db_index=True)  # REMOVED due to DB schema frozen state
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True, null=True, help_text="Summary of the conversation for context injection")

    def __str__(self):
        # Fallback to summary for guest tracking since session_key doesn't exist in DB
        guest_id = (self.summary[:8] if self.summary else "Unknown")
        user_str = self.user.username if self.user else f"Guest ({guest_id})"
        return f"Session {self.id} - {user_str}"

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


