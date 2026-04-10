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

from django.contrib import admin
from .models import (
    Message,
    ChatMemory,
    HariKnowledge,
    GeneratedContent,
    VisitLog,
)

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

    list_display = ("persona_id", "category", "trait_key", "is_active", "updated_at")
    list_filter = ("category", "is_active", "updated_at")
    search_fields = ("category", "trait_key", "trait_value")
    readonly_fields = ("persona_id",)
    verbose_name_plural = "HARI Knowledge"  # 복수형: "HARI Knowledge" (knowledges → knowledge)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GeneratedContent Admin - 생성된 콘텐츠 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    """AI가 생성한 콘텐츠(SNS, 블로그 등)를 관리합니다."""

    list_display = ("content_id", "title_preview", "platform", "is_published", "created_at")
    list_filter = ("platform", "is_published", "created_at")
    search_fields = ("title", "summary")
    readonly_fields = ("content_id", "created_at")
    verbose_name_plural = "Generated Contents"  # 복수형: "Generated Contents"

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 대기 중 — 백엔드 모델 생성 후 주석 해제
# BACKEND_REQUEST.md (2026-04-10) 참고
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# [활성화 방법]
# 1. 백엔드 팀이 BACKEND_REQUEST.md의 5개 모델을 chat/models.py에 추가
# 2. 아래 import 주석 해제
# 3. 각 Admin 클래스 주석 해제
# 4. 서버 재시작

# from .models import (
#     GalleryImage,
#     NewsEvent,
#     ContactSubmission,
#     VideoContent,
#     UserMembership,
# )

# ── GalleryImage Admin ───────────────────────────────────────────────────
# @admin.register(GalleryImage)
# class GalleryImageAdmin(admin.ModelAdmin):
#     """갤러리 이미지 목록 관리. 순서·노출 여부를 목록에서 바로 수정 가능."""
#     list_display  = ("id", "image_url_preview", "caption", "order", "is_active", "created_at")
#     list_editable = ("order", "is_active")
#     list_filter   = ("is_active",)
#     ordering      = ("order",)
#     GalleryImage._meta.verbose_name_plural = "Gallery Images"
#
#     def image_url_preview(self, obj):
#         return obj.image_url[:60] + "..." if len(obj.image_url) > 60 else obj.image_url
#     image_url_preview.short_description = "Image URL"


# ── NewsEvent Admin ──────────────────────────────────────────────────────
# @admin.register(NewsEvent)
# class NewsEventAdmin(admin.ModelAdmin):
#     """뉴스·이벤트 스케줄 관리. 상태·노출 여부를 목록에서 바로 수정 가능."""
#     list_display  = ("id", "title", "event_date", "status", "is_past", "is_active")
#     list_editable = ("status", "is_past", "is_active")
#     list_filter   = ("status", "is_past", "is_active")
#     search_fields = ("title", "description")
#     ordering      = ("-event_date",)
#     NewsEvent._meta.verbose_name_plural = "News Events"


# ── ContactSubmission Admin ──────────────────────────────────────────────
# @admin.register(ContactSubmission)
# class ContactSubmissionAdmin(admin.ModelAdmin):
#     """문의 폼 접수 내역. 읽기 전용 (수정 불가, 조회·삭제만 가능)."""
#     list_display   = ("id", "name", "email", "inquiry_type", "is_read", "created_at")
#     list_editable  = ("is_read",)
#     list_filter    = ("inquiry_type", "is_read", "created_at")
#     search_fields  = ("name", "email", "message")
#     readonly_fields = ("name", "email", "company", "inquiry_type", "message", "created_at")
#     ordering       = ("-created_at",)
#     ContactSubmission._meta.verbose_name_plural = "Contact Submissions"


# ── VideoContent Admin ───────────────────────────────────────────────────
# @admin.register(VideoContent)
# class VideoContentAdmin(admin.ModelAdmin):
#     """YouTube 영상 목록 관리. 순서·노출 여부를 목록에서 바로 수정 가능."""
#     list_display  = ("id", "title", "youtube_url", "order", "is_active", "created_at")
#     list_editable = ("order", "is_active")
#     list_filter   = ("is_active",)
#     search_fields = ("title",)
#     ordering      = ("order",)
#     VideoContent._meta.verbose_name_plural = "Video Contents"


# ── UserMembership Admin ─────────────────────────────────────────────────
# @admin.register(UserMembership)
# class UserMembershipAdmin(admin.ModelAdmin):
#     """사용자 멤버십 플랜·포인트 관리."""
#     list_display   = ("id", "user", "plan", "points", "started_at", "expires_at")
#     list_editable  = ("plan", "points")
#     list_filter    = ("plan",)
#     search_fields  = ("user__username", "user__email")
#     readonly_fields = ("started_at",)
#     UserMembership._meta.verbose_name_plural = "User Memberships"
