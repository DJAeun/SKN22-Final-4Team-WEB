import uuid

from django.contrib.auth import get_user_model
from django.db import models

# PostgreSQL 전용 필드 처리 (로컬 SQLite 호환성을 위해 에러 처리 추가)
try:
    from django.contrib.postgres.fields import ArrayField
    from django.contrib.postgres.indexes import GinIndex
except ImportError:
    # django.contrib.postgres가 없거나 로컬 DB가 SQLite인 경우를 대비한 더미 클래스
    class ArrayField(models.Field):
        def __init__(self, base_field, **kwargs):
            super().__init__(**kwargs)

    class GinIndex(models.Index):
        pass

try:
    from pgvector.django import VectorField
except ImportError:
    # pgvector 모듈이 없는 로컬 환경을 위한 더미 VectorField 클래스
    class VectorField(models.TextField):
        def __init__(self, dimensions=None, *args, **kwargs):
            super().__init__(*args, **kwargs)

User = get_user_model()


class Lorebook(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    keywords = ArrayField(
        models.TextField(),
        help_text="Lorebook trigger keywords",
    )
    lorebook = models.TextField(help_text="Lorebook prompt content")
    priority = models.IntegerField(
        default=50,
        help_text="Priority for evaluating this lorebook rule"
    )
    is_constant = models.BooleanField(
        default=False,
        help_text="If True, always injected into the prompt"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rpg_lorebooks"
        indexes = [
            GinIndex(fields=["keywords"], name="idx_rpg_lorebooks_keywords"),
        ]

    def __str__(self):
        return f"Lorebook({self.id}) keywords={self.keywords}"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="rpg_sessions",
    )
    user_nickname = models.CharField(
        max_length=50,
        help_text="Nickname entered at game start",
    )
    status_window_enabled = models.BooleanField(
        default=True,
        help_text="Toggle for status window display",
    )
    total_tokens = models.IntegerField(
        default=0,
        help_text="Running cumulative token count for hypermemory trigger",
    )
    stress = models.IntegerField(
        default=0,
        help_text="User's stress level in the game"
    )
    crack_stage = models.IntegerField(
        default=0,
        help_text="World crack stage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rpg_sessions"

    def __str__(self):
        return f"Session({self.id}) user={self.user_id} nick={self.user_nickname}"


class StoryProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="story_progress",
    )
    chapter = models.IntegerField()
    transitioned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this chapter was reached",
    )

    class Meta:
        db_table = "rpg_story_progress"
        ordering = ["transitioned_at"]

    def __str__(self):
        return f"Progress({self.session_id}) chapter={self.chapter}"


class ChatLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="chat_logs",
    )
    role = models.CharField(
        max_length=20,
        help_text="user, assistant, or system",
    )
    content = models.TextField(help_text="Content shown to frontend")
    raw_content = models.TextField(
        null=True,
        blank=True,
        help_text="Full LLM response with hidden tags (debug only)",
    )
    status_snapshot = models.JSONField(
        null=True,
        blank=True,
        help_text="Parsed in-game status snapshot for this message",
    )
    image_command = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text='Validated image command for this message, e.g. "daily_thinking"',
    )
    image_url = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Resolved character image URL for this message",
    )
    token_count = models.IntegerField(
        default=0,
        help_text="Token count for this individual message",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rpg_chat_logs"
        ordering = ["id"]

    def __str__(self):
        return f"[{self.role}] {self.content[:30]}"


class MessageEmbedding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="message_embeddings",
    )
    chat_log = models.ForeignKey(
        ChatLog,
        on_delete=models.CASCADE,
        related_name="embeddings",
    )
    embedding = VectorField(dimensions=1536)
    chunk_content = models.TextField(help_text="Source text chunk (KSS-split sentence)")

    class Meta:
        db_table = "rpg_message_embeddings"

    def __str__(self):
        return f"Embedding({self.id}) log={self.chat_log_id}"


class HyperMemory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="hyper_memories",
    )
    location = models.TextField(null=True, blank=True)
    in_game_date = models.DateField(null=True, blank=True)
    in_game_time = models.TimeField(null=True, blank=True)
    location_transition = models.TextField(
        null=True,
        blank=True,
        help_text="e.g. 탕비실 → 회의실",
    )
    characters_present = models.JSONField(
        null=True,
        blank=True,
        help_text='e.g. ["강하리", "민제", "팀장님"]',
    )
    context_overview = models.TextField(
        null=True,
        blank=True,
        help_text="Story summary",
    )
    events = models.JSONField(
        null=True,
        blank=True,
        help_text="List of events/actions",
    )
    infos = models.JSONField(
        null=True,
        blank=True,
        help_text="Newly learned facts/settings",
    )
    emotional_dynamics = models.TextField(
        null=True,
        blank=True,
        help_text="Emotion/relationship/tension",
    )
    dialogues = models.JSONField(
        null=True,
        blank=True,
        help_text='e.g. [{"speaker": "하리", "line": "..."}]',
    )
    last_msg = models.ForeignKey(
        ChatLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hyper_memories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rpg_hyper_memories"
        ordering = ["created_at"]

    def __str__(self):
        return f"HyperMemory({self.id}) session={self.session_id}"


class CharacterImage(models.Model):
    id = models.BigAutoField(primary_key=True)
    clothes = models.CharField(max_length=50, help_text="e.g. suit, daily")
    emotion = models.CharField(max_length=50, help_text="e.g. happy, sad, thinking")
    image_url = models.CharField(max_length=500, help_text="S3 or CDN path")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rpg_character_images"
        unique_together = [("clothes", "emotion")]

    def __str__(self):
        return f"Image({self.clothes}, {self.emotion})"
