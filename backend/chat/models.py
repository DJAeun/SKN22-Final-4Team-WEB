from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Message(models.Model):
    message_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='chat_messages'
    )
    # True = User, False = Hari
    sender_type = models.BooleanField()
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    # Running message sequence number per session
    count = models.SmallIntegerField(default=0)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    used_web_search = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'chat_messages'
        ordering = ['created_at']

    def __str__(self):
        sender = "User" if self.sender_type else "Hari"
        return f"[{sender}] {self.content[:30]}"


class ChatMemory(models.Model):
    memory_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='chat_memories'
    )
    summary = models.TextField(null=True, blank=True)
    keywords = models.CharField(max_length=500, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'chat_memory'

    def __str__(self):
        return f"Memory({self.memory_id}) user={self.user_id}"


class HariKnowledge(models.Model):
    persona_id = models.BigAutoField(primary_key=True, db_column='id')
    category = models.CharField(max_length=255, null=True, blank=True)
    trait_key = models.CharField(max_length=255, null=True, blank=True, db_column='question')
    trait_value = models.TextField(null=True, blank=True, db_column='answer')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    # content_vector VECTOR(1536) is managed via raw SQL (pgvector, not a Django field)

    class Meta:
        managed = False
        db_table = 'hari_knowledge'

    def __str__(self):
        return f"{self.category}: {self.trait_key}"


class UserPersona(models.Model):
    """Per-user facts extracted by the memory pipeline (pgvector-backed)."""
    persona_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='user_personas'
    )
    category = models.TextField(default='')
    trait_key = models.TextField(null=True, blank=True)
    trait_value = models.TextField(default='')
    importance = models.SmallIntegerField(default=5)
    # content_vector is written via raw SQL — pgvector has no Django field type here
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_persona'

    def __str__(self):
        return f"[{self.category}] {self.trait_key}: {self.trait_value[:40]}"


class GeneratedContent(models.Model):
    content_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    platform = models.CharField(max_length=50, null=True, blank=True)
    script_text = models.TextField()
    summary = models.TextField(null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)
    thumbnail_url = models.CharField(max_length=500, null=True, blank=True)
    content_url = models.CharField(max_length=500, null=True, blank=True)
    is_published = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'generated_contents'

    def __str__(self):
        return f"Content({self.content_id}) {self.title or 'untitled'}"


class VisitLog(models.Model):
    log_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', null=True, blank=True,
        related_name='visit_logs'
    )
    visit_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'visit_logs'
        ordering = ['-visit_time']

    def __str__(self):
        return f"Visit({self.log_id}) user={self.user_id} at {self.visit_time}"
