"""
Django Admin 설정 - Chat 앱

Django의 기본 관리자 페이지(/admin)를 통해 Chat 관련 모델들을 관리합니다.
각 ModelAdmin 클래스는 해당 모델의 관리 페이지 UI를 정의합니다.

주요 설정:
- list_display: 목록 페이지에서 표시할 필드
- list_filter: 필터 옵션
- search_fields: 검색 가능한 필드
- readonly_fields: 읽기 전용 필드
- verbose_name_plural: 관리 페이지에 표시되는 모델명 (복수형)

custom methods:
- content_preview: Message 내용 미리보기 (50자 제한)
- summary_preview: ChatMemory 요약 미리보기 (40자 제한)
- persona_data_preview: UserPersona 데이터 미리보기
- title_preview: GeneratedContent 제목 미리보기 (30자 제한)
"""

import logging

from django.contrib import admin, messages
from django.db import connection, transaction
from django.utils import timezone

from .models import (
    Message,
    ChatMemory,
    HariKnowledge,
    GeneratedContent,
    VisitLog,
)

logger = logging.getLogger(__name__)

# Django 관리자 인덱스 표시명 수정 (모델 Meta 없이 덮어쓰기)
ChatMemory._meta.verbose_name_plural = "Chat Memories"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Message Admin - 채팅 메시지 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """사용자와 HARI의 메시지를 관리합니다."""

    list_display = ("message_id", "user", "sender_type", "content_preview", "created_at")
    list_filter = ("sender_type", "created_at")
    search_fields = ("user__username", "content")
    readonly_fields = ("message_id", "created_at")
    verbose_name_plural = "Messages"  # 복수형: "Messages"

    def content_preview(self, obj):
        """메시지 내용을 50자로 미리보기합니다."""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Content"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ChatMemory Admin - 채팅 메모리 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(ChatMemory)
class ChatMemoryAdmin(admin.ModelAdmin):
    """사용자와의 채팅 세션 메모리(요약)를 관리합니다."""

    list_display = ("memory_id", "user", "summary_preview", "ended_at")
    list_filter = ("ended_at",)
    search_fields = ("user__username", "summary", "keywords")
    readonly_fields = ("memory_id",)
    verbose_name_plural = "Chat Memories"  # 복수형: "Chat Memories" (memorys → memories)

    def summary_preview(self, obj):
        """메모리 요약을 40자로 미리보기합니다."""
        return obj.summary[:40] + "..." if obj.summary and len(obj.summary) > 40 else obj.summary
    summary_preview.short_description = "Summary"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HariKnowledge Admin - HARI 지식 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(HariKnowledge)
class HariKnowledgeAdmin(admin.ModelAdmin):
    """HARI의 성격, 관계, 배경 지식 등을 관리합니다."""

    # ── List view ──
    list_display = ("persona_id", "category", "trait_key", "trait_value_preview", "is_active", "updated_at")
    list_editable = ("is_active",)
    list_filter = ("category", "is_active", "updated_at")
    search_fields = ("category", "trait_key", "trait_value")
    ordering = ("-updated_at",)
    list_per_page = 30

    # ── Change form ──
    readonly_fields = ("persona_id", "updated_at")
    fieldsets = (
        ("지식 내용", {
            "fields": ("category", "trait_key", "trait_value"),
            "description": "하리의 성격, 말투, 역사, 관계 등을 정의합니다.",
        }),
        ("상태", {
            "fields": ("is_active", "updated_at"),
        }),
        ("시스템 정보", {
            "fields": ("persona_id",),
            "classes": ("collapse",),
        }),
    )

    # ── Bulk actions ──
    actions = ["activate_selected", "deactivate_selected"]

    verbose_name_plural = "HARI Knowledge"

    @admin.action(description="선택한 지식을 활성화 (is_active = True)")
    def activate_selected(self, request, queryset):
        updated = queryset.update(is_active=True, updated_at=timezone.now())
        self.message_user(request, f"{updated}개 항목이 활성화되었습니다.")

    @admin.action(description="선택한 지식을 비활성화 (is_active = False)")
    def deactivate_selected(self, request, queryset):
        updated = queryset.update(is_active=False, updated_at=timezone.now())
        self.message_user(request, f"{updated}개 항목이 비활성화되었습니다.")

    def trait_value_preview(self, obj):
        """trait_value를 60자로 미리보기합니다."""
        if not obj.trait_value:
            return "-"
        return obj.trait_value[:60] + "..." if len(obj.trait_value) > 60 else obj.trait_value
    trait_value_preview.short_description = "Trait Value"

    def has_delete_permission(self, request, obj=None):
        """하드 삭제를 방지합니다. is_active로 소프트 삭제하세요."""
        return False

    def save_model(self, request, obj, form, change):
        """
        Save the knowledge entry and generate/update the content_vector embedding.
        Wrapped in a transaction so both the ORM save and the raw SQL vector update
        succeed or fail together.
        """
        from .memory_vector import embed_text, _vector_to_str

        trait_value_changed = not change or "trait_value" in form.changed_data

        try:
            with transaction.atomic():
                super().save_model(request, obj, form, change)

                if trait_value_changed and obj.trait_value:
                    text = f"[{obj.category}] {obj.trait_key}: {obj.trait_value}"
                    vector = embed_text(text)
                    if vector is not None:
                        vector_str = _vector_to_str(vector)
                        with connection.cursor() as cur:
                            cur.execute(
                                "UPDATE hari_knowledge SET content_vector = %s::vector WHERE id = %s",
                                [vector_str, obj.persona_id],
                            )
                    else:
                        messages.warning(
                            request,
                            "지식이 저장되었지만 벡터 임베딩 생성에 실패했습니다. "
                            "OpenAI API 상태를 확인하세요. 임베딩 없이는 벡터 검색에서 제외됩니다.",
                        )
                        logger.error("Embedding generation failed for hari_knowledge id=%s", obj.persona_id)
        except Exception as e:
            logger.error("Failed to save hari_knowledge id=%s: %s", obj.persona_id, e, exc_info=True)
            messages.error(
                request,
                f"저장 중 오류가 발생했습니다: {e}",
            )
            raise


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GeneratedContent Admin - 생성된 콘텐츠 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    """AI가 생성한 유튜브 영상 콘텐츠를 관리합니다."""

    list_display = ("content_id", "title_preview", "platform", "is_published", "created_at")
    list_editable = ("is_published",)
    list_filter = ("platform", "is_published", "created_at")
    search_fields = ("title", "summary")
    readonly_fields = ("content_id", "created_at")
    ordering = ("content_id",)
    verbose_name_plural = "Generated Contents"

    def get_changeform_initial_data(self, request):
        """새 콘텐츠 등록 시 플랫폼 기본값을 'YouTube'로 설정합니다."""
        return {'platform': 'YouTube'}

    def title_preview(self, obj):
        """콘텐츠 제목을 30자로 미리보기합니다."""
        return obj.title[:30] + "..." if obj.title and len(obj.title) > 30 else obj.title
    title_preview.short_description = "Title"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VisitLog Admin - 방문 기록 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    """사용자의 사이트 방문 기록을 관리합니다."""

    list_display = ("log_id", "user", "visit_time")
    list_filter = ("visit_time",)
    search_fields = ("user__username",)
    readonly_fields = ("log_id", "visit_time")
    verbose_name_plural = "Visit Logs"  # 복수형: "Visit Logs"


