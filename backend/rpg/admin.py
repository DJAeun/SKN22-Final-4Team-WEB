from django.contrib import admin

from .models import (
    CharacterImage,
    ChatLog,
    HyperMemory,
    Lorebook,
    MessageEmbedding,
    Session,
    StoryProgress,
)


@admin.register(Lorebook)
class LorebookAdmin(admin.ModelAdmin):
    list_display = ("id", "keywords", "is_active", "created_at")
    list_filter = ("is_active",)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "user_nickname", "total_tokens", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_nickname", "user__username")


@admin.register(StoryProgress)
class StoryProgressAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "chapter", "transitioned_at")


@admin.register(ChatLog)
class ChatLogAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "role", "token_count", "created_at")
    list_filter = ("role",)


@admin.register(MessageEmbedding)
class MessageEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "chat_log")


@admin.register(HyperMemory)
class HyperMemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "session", "location", "in_game_date", "created_at")


@admin.register(CharacterImage)
class CharacterImageAdmin(admin.ModelAdmin):
    list_display = ("id", "clothes", "emotion", "is_active", "image_url")
    list_filter = ("clothes", "emotion", "is_active")
