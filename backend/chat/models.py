from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatSession(models.Model):
    session_id = models.CharField(max_length=255, primary_key=True)
    is_active = models.BooleanField(default=True, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'chat_session'

    def __str__(self):
        user_str = self.user.username if self.user else "Guest"
        return f"Session {self.session_id} - {user_str}"

class Message(models.Model):
    message_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, db_column='session_id')
    
    # True for User, False for Hari
    sender_type = models.BooleanField()
    content = models.TextField()
    is_read = models.BooleanField(default=False, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        sender = "User" if self.sender_type else "Hari"
        return f"[{sender}] {self.content[:30]}"