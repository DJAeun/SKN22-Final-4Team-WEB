# 백엔드/데브옵스/AWS 협의 필요 사항

이 파일은 프론트엔드에서 다른 팀(백엔드, 데브옵스, AWS)에 요청하는 작업들을 날짜별로 관리합니다.
협의 필요시 아래 섹션에 추가해주세요.

---

## 📅 2026-04-08 (화)

### 1. 홈페이지 - 회원가입 / 로그인 (모달)

**프론트엔드 작업:**
- 이메일 입력 시 실시간 검증 UI 추가 (아이콘 + 메시지)
- 검증 완료되지 않으면 회원가입 불가

**백엔드 작업:**
- `/api/auth/verify-email/` 엔드포인트 구현

---

## 2. 회원가입 페이지 (/accounts/signup/)

**프론트엔드 작업:**
- 홈페이지 모달과 동일한 이메일 검증 UI 적용

**백엔드 작업:**
- 위의 1번과 동일한 API 사용

---

## API 명세: `/api/auth/verify-email/`

| 항목 | 내용 |
|------|------|
| **HTTP Method** | POST |
| **인증** | CSRF 토큰 필수 |
| **요청 본문** | `{"email": "user@example.com"}` |
| **응답 (미등록)** | `{"valid": true, "available": true, "message": "사용 가능한 이메일입니다."}` |
| **응답 (등록됨)** | `{"valid": true, "available": false, "message": "이미 가입된 이메일입니다."}` |
| **구현 로직** | 1. 이메일 형식 검증 2. User.objects.filter(email=email).exists() 로 DB 확인 3. available 필드로 결과 반환 |

**프론트엔드 처리 방식:**
- 요청: 이메일 입력 후 500ms 딜레이로 API 호출
- 응답: available 값에 따라 ✅(가능) 또는 ❌(불가) 표시
- 검증 완료: window.emailValidated = true/false 로 상태 관리

---

## 📅 2026-04-10 (목) — Admin 관리 기능 확장

### [우선순위 높음] Admin에서 관리할 5개 모델 생성 요청

사이트의 주요 콘텐츠(갤러리·뉴스·비디오·멤버십·문의)가 현재 HTML에 하드코딩되어 있어
관리자 페이지에서 수정이 불가능한 상태입니다.
아래 5개 모델을 `chat/models.py`에 추가해주시면 프론트가 즉시 admin 등록 코드를 활성화합니다.
(admin.py 코드는 이미 준비되어 있으며 주석 해제만 하면 됩니다)

---

#### 모델 1. `GalleryImage` — 갤러리 이미지 관리

```python
class GalleryImage(models.Model):
    image_url   = models.URLField(help_text="이미지 URL (S3 또는 외부)")
    caption     = models.CharField(max_length=200, blank=True, help_text="이미지 설명")
    order       = models.PositiveIntegerField(default=0, help_text="표시 순서 (낮을수록 앞)")
    is_active   = models.BooleanField(default=True, help_text="사이트 노출 여부")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'gallery_image'
        ordering  = ['order']
        verbose_name_plural = "Gallery Images"

    def __str__(self):
        return f"GalleryImage({self.id}) order={self.order}"
```

**왜 필요한가:** 현재 갤러리 이미지는 `_s3_gallery.html`에 하드코딩되어 있어
사진을 추가/삭제하려면 개발자가 HTML을 직접 수정해야 함.
이 모델이 생기면 admin에서 URL 입력만으로 갤러리를 관리할 수 있음.

---

#### 모델 2. `NewsEvent` — 뉴스/이벤트 관리

```python
class NewsEvent(models.Model):
    STATUS_CHOICES = [
        ('upcoming', '예정'),
        ('ongoing',  '진행 중'),
        ('tbd',      '미정'),
        ('past',     '완료'),
    ]
    title       = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    event_date  = models.DateField(null=True, blank=True, help_text="행사 날짜")
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_past     = models.BooleanField(default=False, help_text="지난 행사 여부")
    is_active   = models.BooleanField(default=True, help_text="사이트 노출 여부")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'news_event'
        ordering  = ['-event_date']
        verbose_name_plural = "News Events"

    def __str__(self):
        return f"{self.title} ({self.status})"
```

**왜 필요한가:** 뉴스·스케줄이 `news.html`에 하드코딩되어 있어
새 일정 추가·완료 처리를 HTML 수정 없이 할 수 없음.

---


#### 모델 4. `VideoContent` — YouTube 비디오 관리

```python
class VideoContent(models.Model):
    title         = models.CharField(max_length=200)
    youtube_url   = models.URLField(help_text="YouTube 영상 URL")
    thumbnail_url = models.URLField(blank=True, help_text="썸네일 URL (비워두면 YouTube 자동)")
    order         = models.PositiveIntegerField(default=0, help_text="표시 순서")
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'video_content'
        ordering  = ['order']
        verbose_name_plural = "Video Contents"

    def __str__(self):
        return f"{self.title}"
```

**왜 필요한가:** YouTube 영상 목록이 `_s4_video.html`에 하드코딩되어 있어
새 영상 추가 시 HTML 직접 수정 필요.

---

#### 모델 5. `UserMembership` — 멤버십 구독 현황

```python
from django.conf import settings

class UserMembership(models.Model):
    PLAN_CHOICES = [
        ('free',     'Free'),
        ('fan_plus', 'Fan+'),
        ('vip',      'VIP'),
    ]
    user       = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='membership'
    )
    plan       = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    points     = models.IntegerField(default=0, help_text="보유 포인트")
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="만료일 (null=무기한)")

    class Meta:
        db_table  = 'user_membership'
        verbose_name_plural = "User Memberships"

    def __str__(self):
        return f"{self.user.username} - {self.plan}"
```

**왜 필요한가:** 현재 사용자의 멤버십 플랜·포인트 정보를 admin에서 볼 수 없음.
이 모델이 있어야 특정 사용자에게 VIP 부여, 포인트 지급 등을 admin에서 처리 가능.

---

#### 요약 체크리스트 (백엔드)

| 모델 | 파일 | 추가 views.py 작업 |
|---|---|---|
| `GalleryImage` | `chat/models.py` | 없음 |
| `NewsEvent` | `chat/models.py` | 없음 |
| `ContactSubmission` | `chat/models.py` | `contact_form` 뷰에 저장 코드 추가 |
| `VideoContent` | `chat/models.py` | 없음 |
| `UserMembership` | `chat/models.py` | 없음 |

모델 추가 후 `makemigrations` + `migrate` 실행 필요.
프론트는 admin.py 주석 해제만 하면 즉시 admin에 반영됩니다.

---

## 📅 2026-04-09 (수)

### 멤버십 페이지 - 구독 취소 기능

**프론트엔드:**
- membership.html에 구독 취소 버튼 추가 (구독 중인 사용자에게만 표시)
- 구독 취소 버튼 클릭 시 확인 모달 후 요청

**백엔드 작업:**
1. membership.html context에 필요한 변수 추가:
   - `is_subscribed` (bool): 현재 사용자 구독 여부
   - `current_plan` (str, 선택사항): 현재 플랜 (fan/fanplus/bori)

2. 구독 취소 엔드포인트 구현:
   - `/api/cancel-subscription/` (POST) 또는 `/membership/cancel/` (POST)
   - 인증 필수, CSRF 토큰 필수
   - 성공 응답: `{"success": true, "message": "구독이 취소되었습니다."}`
   - 오류 응답: `{"success": false, "error": "구독 정보가 없습니다."}`

---

## 📅 2026-04-13 (일) — /admin/ 관리자 페이지 기능 확장

> 프론트엔드가 `/admin/` (Django admin) 커스텀 템플릿을 모두 구축했습니다.  
> 아래 항목은 백엔드 모델·뷰가 없어 **현재 admin에서 placeholder만 표시** 중인 기능입니다.  
> 구현 순서는 우선순위 순으로 정렬했습니다.

---

### [우선순위 1] 관리자 대시보드 KPI 컨텍스트 — `/admin/`

Django admin의 `index.html` 템플릿은 현재 `app_list`와 `recent_actions`만 받습니다.  
대시보드에 실시간 통계를 표시하려면 `AdminSite.index()` 뷰를 오버라이드해서 아래 변수를 추가해야 합니다.

**백엔드 작업:**

`config/urls.py` 또는 별도 파일에 커스텀 AdminSite 클래스 추가:

```python
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.utils import timezone
from chat.models import Message, VisitLog

class HariAdminSite(AdminSite):
    def index(self, request, extra_context=None):
        today = timezone.now().date()
        User = get_user_model()
        extra_context = extra_context or {}
        extra_context.update({
            'kpi_new_users_today':    User.objects.filter(date_joined__date=today).count(),
            'kpi_chat_count_today':   Message.objects.filter(created_at__date=today, sender_type=True).count(),
            'kpi_total_users':        User.objects.count(),
            'kpi_today_visits':       VisitLog.objects.filter(visit_time__date=today).count(),
        })
        return super().index(request, extra_context)

admin_site = HariAdminSite(name='admin')
```

| 변수명 | 설명 |
|---|---|
| `kpi_new_users_today` | 오늘 신규 가입자 수 |
| `kpi_chat_count_today` | 오늘 채팅 메시지 수 (유저 발신) |
| `kpi_total_users` | 전체 유저 수 |
| `kpi_today_visits` | 오늘 방문 수 |

---

### [우선순위 2] 롤플레잉 시나리오 버전 히스토리 모델

**현재 상황:** Lorebook 편집 시 이전 버전으로 롤백 불가  
**프론트 준비:** 편집 폼에 버전 히스토리 UI 공간 확보됨 (백엔드 연결만 필요)

**백엔드 작업:** `rpg/models.py`에 추가 (기존 모델 수정 없이 새 모델만 추가)

```python
class LorebookVersion(models.Model):
    lorebook = models.ForeignKey(
        'Lorebook', on_delete=models.CASCADE, related_name='versions'
    )
    lorebook_text = models.TextField(help_text="저장 시점의 lorebook 내용")
    keywords_snapshot = models.JSONField(help_text="저장 시점의 keywords")
    version_number = models.PositiveIntegerField()
    saved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rpg_lorebook_versions'
        ordering = ['-version_number']

    def __str__(self):
        return f"Lorebook({self.lorebook_id}) v{self.version_number}"
```

**추가 요청 (admin.py):** Lorebook 저장 시 자동 버전 생성 signal 또는 `save_model()` 오버라이드

```python
# rpg/admin.py — LorebookAdmin에 추가
def save_model(self, request, obj, form, change):
    super().save_model(request, obj, form, change)
    if change:  # 수정 시에만
        last_v = LorebookVersion.objects.filter(lorebook=obj).order_by('-version_number').first()
        next_v = (last_v.version_number + 1) if last_v else 1
        LorebookVersion.objects.create(
            lorebook=obj,
            lorebook_text=obj.lorebook,
            keywords_snapshot=obj.keywords,
            version_number=next_v,
            saved_by=request.user,
        )
```

---

### [우선순위 3] 채팅 금지어 관리 모델

**현재 상황:** 금지어를 admin에서 추가/삭제할 방법 없음  
**프론트 준비:** 관리자 대시보드 채팅 모니터링 섹션에 공간 확보됨

**백엔드 작업:** `chat/models.py`에 추가 (새 모델)

```python
class BannedWord(models.Model):
    word = models.CharField(max_length=100, unique=True, help_text="금지 단어/문구")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'banned_words'
        ordering = ['word']
        verbose_name = "금지어"
        verbose_name_plural = "금지어 관리"

    def __str__(self):
        return self.word
```

---

### [우선순위 4] 공지 배너 & 이벤트 모델

**현재 상황:** 사이트 상단 공지 배너가 하드코딩, admin에서 수정 불가  
**프론트 준비:** admin 대시보드에 placeholder 카드 존재

**백엔드 작업:** `chat/models.py`에 추가

```python
class SiteBanner(models.Model):
    message = models.CharField(max_length=300, help_text="배너에 표시할 문구")
    link_url = models.URLField(blank=True, help_text="클릭 시 이동 URL (선택)")
    is_active = models.BooleanField(default=False, help_text="현재 배너 ON/OFF")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'site_banners'
        verbose_name = "사이트 배너"
        verbose_name_plural = "사이트 배너 관리"

    def __str__(self):
        return f"{'[ON]' if self.is_active else '[OFF]'} {self.message[:50]}"


class SiteEvent(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'site_events'
        ordering = ['-starts_at']
        verbose_name = "이벤트"
        verbose_name_plural = "이벤트 관리"

    def __str__(self):
        return self.title
```

---

### [우선순위 5] AI API 사용량 추적 모델

**현재 상황:** LLM / 이미지 / TTS API 비용 admin에서 볼 수 없음  
**프론트 준비:** admin 대시보드 AI & 하리 섹션에 placeholder 존재

**백엔드 작업:** `chat/models.py`에 추가

```python
class ApiUsageLog(models.Model):
    API_TYPE_CHOICES = [
        ('llm', 'LLM (텍스트 생성)'),
        ('image', '이미지 생성'),
        ('tts', 'TTS (음성 합성)'),
        ('embedding', '임베딩'),
    ]
    api_type = models.CharField(max_length=20, choices=API_TYPE_CHOICES)
    tokens_used = models.IntegerField(default=0, help_text="사용 토큰 수")
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0, help_text="추정 비용 (USD)")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'api_usage_logs'
        ordering = ['-created_at']
        verbose_name = "API 사용 로그"
        verbose_name_plural = "AI API 사용량"

    def __str__(self):
        return f"[{self.api_type}] {self.tokens_used}tok / ${self.cost_usd}"
```

---

### [우선순위 6] 관리자 접근 로그

**현재 상황:** 관리자가 채팅 로그 등 민감한 데이터에 접근해도 기록 없음

**백엔드 작업:** `chat/models.py`에 추가

```python
class AdminAccessLog(models.Model):
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='admin_access_logs'
    )
    path = models.CharField(max_length=500, help_text="접근한 admin URL")
    action = models.CharField(max_length=100, blank=True, help_text="수행한 액션 설명")
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_access_logs'
        ordering = ['-accessed_at']
        verbose_name = "관리자 접근 로그"

    def __str__(self):
        return f"{self.admin_user.username} → {self.path}"
```

**미들웨어 추가 요청:**
```python
# chat/middleware.py 또는 새 파일
class AdminAccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/admin/') and request.user.is_authenticated and request.user.is_staff:
            from chat.models import AdminAccessLog
            AdminAccessLog.objects.create(
                admin_user=request.user,
                path=request.path,
            )
        return response
```

---

### 요약 체크리스트 (백엔드)

| 기능 | 모델/작업 | 파일 | 우선순위 |
|---|---|---|---|
| 대시보드 KPI | `HariAdminSite` 클래스 + `index()` 오버라이드 | `config/urls.py` 또는 신규 파일 | 🔴 높음 |
| 시나리오 버전 히스토리 | `LorebookVersion` 모델 + `save_model()` 오버라이드 | `rpg/models.py`, `rpg/admin.py` | 🔴 높음 |
| 채팅 금지어 | `BannedWord` 모델 | `chat/models.py` | 🟡 중간 |
| 공지 배너 | `SiteBanner` 모델 | `chat/models.py` | 🟡 중간 |
| 이벤트 관리 | `SiteEvent` 모델 | `chat/models.py` | 🟡 중간 |
| AI API 사용량 | `ApiUsageLog` 모델 | `chat/models.py` | 🟢 낮음 |
| 관리자 접근 로그 | `AdminAccessLog` 모델 + middleware | `chat/models.py`, middleware | 🟢 낮음 |

모든 모델 추가 후 `makemigrations` + `migrate` 실행 필요.  
프론트는 admin.py에 모델 등록만 하면 즉시 admin에 반영됩니다.

---

## 📅 2026-04-14 (월) — 배포 런타임 에러 2건

> 배포 자체는 성공 (Health: Green, HTTP 200 정상 응답 중)  
> 하지만 아래 2개의 런타임 에러가 서버 로그에서 확인됨

---

### [긴급] OpenAI 토큰 초과 에러

**에러 로그:**
```
openai.BadRequestError: Error code: 400
Input tokens exceed the configured limit of 272000 tokens.
Your messages resulted in 428548 tokens.
```

**발생 위치:** `consumers.py` 또는 `engine.py` — 채팅 대화 기록을 OpenAI API로 전달하는 부분

**현상:**
- 대화가 길어진 사용자의 채팅 요청이 중간에 실패함
- 현재 대화 요약 기능이 있지만, 일부 케이스에서 428,548 토큰까지 누적되어 API 한도(272,000) 초과

**요청:**
- 대화 히스토리를 API에 전달하기 전에 최대 토큰 수 제한 로직 추가
  - 예: 오래된 메시지부터 잘라내기 (sliding window) 또는 강제 요약 트리거

---

### [보통] LangSmith API 403 Forbidden 에러

**에러 로그:**
```
langsmith.utils.LangSmithError: Failed to POST https://api.smith.langchain.com/runs/multipart
HTTPError('403 Client Error: Forbidden')
```

**현상:**
- LangSmith로 실행 로그를 전송할 때 403 에러 반복 발생
- 기능에 직접 영향은 없으나 로그가 계속 쌓임

**요청:**
- AWS EB 환경변수에서 `LANGCHAIN_API_KEY` 값 확인 및 갱신
- 또는 LangSmith 비활성화: `LANGCHAIN_TRACING_V2=false` 환경변수 설정

---

## 📅 2026-04-14 (화) — 영상 숨김/노출 기능 연동

홈페이지와 영상 페이지의 영상 목록을 관리자 페이지와 연동하기 위해 아래 작업을 요청합니다.

### 1. 관리자 페이지 수정 (`chat/admin.py`)

**요청 사항:**
- `GeneratedContentAdmin` 클래스의 목록 화면에서 '공개 여부'를 바로 수정할 수 있도록 설정 변경.

**코드 제안:**
```python
# chat/admin.py
@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ("content_id", "title_preview", "platform", "is_published", "created_at")
    list_editable = ("is_published",)  # 이 라인 추가 요청
    # ... 기존 코드
```

### 2. 뷰(View) 컨텍스트 추가 (`chat/views.py`)

**요청 사항:**
- 홈페이지 및 영상 페이지에서 DB에 등록된 '공개 상태'의 영상만 보이도록 context 전달 필요.

**코드 제안:**
```python
# chat/views.py

def homepage(request):
    _try_jwt_auth(request)
    # 아래 로직 추가 요청
    contents = GeneratedContent.objects.filter(is_published=True).order_by('-created_at')[:10]
    return render(request, 'frontend/homepage.html', {'contents': contents})

def video_page(request):
    # 아래 로직 추가 요청
    contents = GeneratedContent.objects.filter(is_published=True).order_by('-created_at')
    return render(request, 'frontend/video.html', {'contents': contents})
```

---

### 3. 데이터베이스 마이그레이션 확인
- 로컬 테스트용 `hari_knowledge` 테이블 생성은 완료되었습니다.
- 배포 환경의 `GeneratedContent` 데이터가 정상적으로 조회되는지 확인 필요합니다.

---

## 📅 2026-04-14 (월) — 어드민 하리지식 페이지 서버 접근 불가

### [긴급] pgvector PostgreSQL 확장 미설치

**현상:** `/admin/chat/hariknowledge/` 로컬에서는 정상 접근되지만, 서버에서는 에러 발생하여 페이지 진입 불가

**원인:** `chat/migrations/0010_add_user_memory.py` 마이그레이션이 `VECTOR(1536)` 타입과 HNSW 인덱스를 사용합니다.
이는 PostgreSQL에 `pgvector` 확장이 설치되어 있어야만 동작합니다.
로컬 SQLite에서는 해당 타입이 무시되어 정상 동작하지만, 서버 RDS PostgreSQL에서는 확장이 없어 실패합니다.

**요청:** AWS RDS PostgreSQL 인스턴스에서 아래 SQL 실행:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
이후 배포 시 마이그레이션이 자동 실행되어 정상화됩니다.

**관련 파일:** `chat/migrations/0010_add_user_memory.py`

---

## 📅 2026-04-16 (수) — 관리자 대시보드 방문자 집계 버그

### [보통] 서비스 현황 - 방문자 수 기간별 역전 현상

**현상:**  
관리자 대시보드 "서비스 현황" 탭에서 기간 선택 시,  
**일별 방문자 합산이 연별 방문자 합산보다 높게** 나타나는 논리적 역전 현상 발생.

**원인:**  
`chat/views.py` 412번째 줄에서 방문자를 `Count('user', distinct=True)`로 집계함.  
이는 **기간 버킷마다 중복 제거**를 적용하기 때문에, 같은 사용자가 여러 날 방문하면  
일별에서는 날마다 1씩 합산되지만, 연별에서는 1년에 1번만 카운트됨.

```python
# chat/views.py:412 (현재 코드)
visit_data = query_by_period(VisitLog, 'visit_time', {}, count_expr=Count('user', distinct=True))
```

| 기간 | 계산 방식 | 예시 (사용자 100명이 매일 접속) |
|---|---|---|
| 일별 | 7일 각각 distinct → 합산 | 100 × 7 = **700** |
| 연별 | 2026년 전체 distinct → 합산 | 100명 → **100** |

채팅/롤플레잉은 `Count('pk')` 기반이라 문제 없음.

**요청:**  
방문자 집계 방식을 아래 중 하나로 변경 요청:

**방법 A — 방문 건수 기준 (세션/페이지뷰 개념)**
```python
visit_data = query_by_period(VisitLog, 'visit_time', {})  # count_expr 제거 → Count('pk') 기본값
```

**방법 B — 기간 전체의 고유 방문자 수 (별도 집계)**
```python
# 기간 내 전체 unique user 수를 별도로 계산해서 카드에 표시
# 예: VisitLog.objects.filter(visit_time__date__gte=start).aggregate(Count('user', distinct=True))
```

프론트 변경 없이 백엔드 수정만으로 해결 가능합니다.
