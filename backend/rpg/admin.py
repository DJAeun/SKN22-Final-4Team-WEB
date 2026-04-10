"""
Django Admin 설정 - RPG 앱

역할극(RPG) 게임 관련 모델들을 Django 관리자 페이지(/admin)에서 관리합니다.

주요 기능:
- Lorebook: 게임 배경 및 설정 관리
- Session: 사용자의 게임 진행 상태
- StoryProgress: 챕터별 진행도
- ChatLog: 게임 내 대화 기록
- MessageEmbedding: 대화 벡터 임베딩
- HyperMemory: 게임 진행 중 발생한 주요 사건/메모리
- CharacterImage: 캐릭터 이미지 관리

각 ModelAdmin은 관리 페이지의 UI/UX를 정의합니다.
"""

from django.contrib import admin

from .models import (
    CharacterImage,
    HyperMemory,
    Lorebook,
    Session,
)

# Django 관리자 인덱스 표시명 수정 (모델 Meta 없이 덮어쓰기)
HyperMemory._meta.verbose_name_plural = "Hyper Memories"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Lorebook Admin - 게임 배경/설정 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(Lorebook)
class LorebookAdmin(admin.ModelAdmin):
    """
    게임의 배경 설정, 세계관, 등장인물 정보 등을 관리합니다.

    - keywords: 룰북이 적용될 키워드 (배열)
    - priority: 적용 우선순위 (높을수록 먼저 적용)
    - is_constant: 항상 프롬프트에 포함할지 여부
    """

    list_display = ("id", "keywords", "is_active", "created_at")
    list_filter = ("is_active",)
    verbose_name_plural = "Lorebooks"  # 복수형: "Lorebooks"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Session Admin - 게임 세션 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """
    사용자의 게임 진행 세션을 관리합니다.

    - user_nickname: 게임에서 사용 중인 닉네임
    - total_tokens: 누적 토큰 수 (AI 응답 비용 추적)
    - stress: 게임 내 스트레스 레벨
    - crack_stage: 세계 균열 진행도
    """

    list_display = ("id", "user", "user_nickname", "total_tokens", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user_nickname", "user__username")
    verbose_name_plural = "Sessions"  # 복수형: "Sessions"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HyperMemory Admin - 하이퍼 메모리 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(HyperMemory)
class HyperMemoryAdmin(admin.ModelAdmin):
    """
    게임 진행 중 발생한 주요 사건, 대사, 분위기 등을 구조화된 메모리로 저장합니다.

    - location: 현재 위치
    - in_game_date/time: 게임 내 시간
    - characters_present: 현재 등장 중인 캐릭터
    - context_overview: 현재 상황 요약
    - emotional_dynamics: 캐릭터들의 감정 및 관계
    - dialogues: 주요 대사 기록
    """

    list_display = ("id", "session", "location", "in_game_date", "created_at")
    verbose_name_plural = "Hyper Memories"  # 복수형: "Hyper Memories" (memorys → memories)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CharacterImage Admin - 캐릭터 이미지 관리
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@admin.register(CharacterImage)
class CharacterImageAdmin(admin.ModelAdmin):
    """
    게임 내에서 사용되는 캐릭터 이미지를 관리합니다.

    - clothes: 캐릭터의 복장 상태
    - emotion: 감정 표현 (happy, sad, angry, etc.)
    - image_url: 실제 이미지 URL
    """

    list_display = ("id", "clothes", "emotion", "is_active", "image_url")
    list_filter = ("clothes", "emotion", "is_active")
    verbose_name_plural = "Character Images"  # 복수형: "Character Images"
