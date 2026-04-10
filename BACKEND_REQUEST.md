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

#### 모델 3. `ContactSubmission` — 문의 폼 접수 저장

```python
class ContactSubmission(models.Model):
    name         = models.CharField(max_length=100)
    email        = models.EmailField()
    company      = models.CharField(max_length=100, blank=True)
    inquiry_type = models.CharField(max_length=50)
    message      = models.TextField()
    is_read      = models.BooleanField(default=False, help_text="관리자 확인 여부")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table  = 'contact_submission'
        ordering  = ['-created_at']
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"{self.name} ({self.email}) - {self.inquiry_type}"
```

**왜 필요한가:** 현재 `contact_form` 뷰가 폼 데이터를 DB에 저장하지 않아
어떤 문의가 왔는지 admin에서 확인 불가. 이 모델과 함께 `views.py`의
`contact_form` 함수에 `ContactSubmission.objects.create(...)` 한 줄 추가 필요.

**추가 요청 (views.py):**
```python
# chat/views.py contact_form 함수 안에 추가
ContactSubmission.objects.create(
    name=name, email=email,
    company=company, inquiry_type=inquiry_type, message=message
)
```

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
