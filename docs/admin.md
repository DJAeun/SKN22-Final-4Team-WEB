# HARI 관리자 페이지 완전 가이드

---

## 목차

1. [관리자 페이지란?](#1-관리자-페이지란)
2. [접속 방법](#2-접속-방법)
3. [왜 Django Admin인가?](#3-왜-django-admin인가)
4. [파일 구조 설명](#4-파일-구조-설명)
5. [기능별 사용법](#5-기능별-사용법)
6. [디자인 커스터마이징 방법](#6-디자인-커스터마이징-방법)
7. [자주 하는 작업](#7-자주-하는-작업)
8. [주의사항](#8-주의사항)

---

## 1. 관리자 페이지란?

HARI 프로젝트의 관리자 페이지(`/admin/`)는 **Django가 기본 제공하는 관리자 인터페이스**를 우리 프로젝트 디자인에 맞게 커스터마이징한 것입니다.

### 한마디로 요약

> 코드 없이 데이터베이스를 보고, 추가하고, 수정하고, 삭제할 수 있는 웹 UI

예를 들어:
- 하리의 지식(성격, 배경 등)을 수정하고 싶을 때 → 관리자 페이지에서 직접 수정
- 특정 사용자를 비활성화하고 싶을 때 → 관리자 페이지에서 클릭 한 번
- 생성된 콘텐츠를 발행/취소하고 싶을 때 → 관리자 페이지에서 처리
- 채팅 메시지 기록을 확인하고 싶을 때 → 관리자 페이지에서 검색

---

## 2. 접속 방법

### URL
```
http://localhost:8000/admin/          (로컬 개발)
https://[서버도메인]/admin/           (배포 서버)
```

### 로그인 조건
- Django superuser 또는 staff 계정이어야 함
- 일반 사용자는 접근 불가 (자동으로 차단됨)

### 계정 만드는 법 (최초 1회)
```bash
python manage.py createsuperuser
```
이름, 이메일, 비밀번호를 입력하면 관리자 계정 생성 완료.

---

## 3. 왜 Django Admin인가?

### Django Admin을 선택한 이유

| 이유 | 설명 |
|---|---|
| **무료로 제공** | Django 설치하면 자동으로 포함됨, 별도 개발 필요 없음 |
| **안전함** | Django가 SQL Injection, CSRF, XSS 등을 자동으로 방어 |
| **모든 모델 자동 연동** | `admin.py`에 등록만 하면 UI가 자동 생성됨 |
| **검색/필터 내장** | 코드 거의 없이 검색창, 필터, 정렬 기능이 생김 |
| **권한 관리 내장** | 어떤 직원이 어떤 데이터에만 접근할지 세부 설정 가능 |
| **커스터마이징 가능** | 우리가 한 것처럼 템플릿을 덮어씌워 디자인 변경 가능 |

### 커스텀 admin-panel을 제거한 이유
기존에 `/admin-panel/`이라는 별도의 커스텀 대시보드가 있었지만 제거했습니다.

- Django Admin이 이미 같은 기능을 더 완성도 있게 제공함
- 두 개의 관리자 페이지를 유지하면 코드 중복이 발생하고 관리가 복잡해짐
- Django Admin에 집중하여 하나를 제대로 만드는 것이 낫다는 판단

---

## 4. 파일 구조 설명

관리자 페이지와 관련된 파일은 총 5개입니다.

```
backend/
├── templates/
│   └── admin/
│       ├── base_site.html     ← 전체 디자인 (헤더·사이드바·폰트·색상)
│       ├── index.html         ← 대시보드 (첫 화면)
│       ├── change_list.html   ← 목록 페이지 (모델 데이터 목록)
│       └── change_form.html   ← 수정 폼 (데이터 추가/편집 화면)
├── chat/
│   └── admin.py               ← Chat 앱 모델 등록 및 표시 설정
└── rpg/
    └── admin.py               ← RPG 앱 모델 등록 및 표시 설정
```

---

### `base_site.html` — 전체 디자인의 핵심

**역할:** Django Admin의 모든 페이지(목록, 수정 폼, 대시보드 등)에 공통으로 적용되는 스타일 정의

**왜 이 파일인가?**
Django Admin은 내부적으로 `admin/base.html` → `admin/base_site.html` 순서로 상속합니다.
`base_site.html`을 우리가 만들면 Django가 자동으로 기본 파일 대신 우리 파일을 사용합니다.

**무엇을 바꿨는가?**

| 항목 | 변경 전 | 변경 후 | 이유 |
|---|---|---|---|
| 폰트 | 시스템 기본 폰트 | Inter | 실무 어드민에서 가장 많이 쓰이는 폰트 |
| 헤더 색상 | 핑크/갈색 그라디언트 | Slate Navy (`#0f172a`) | 고급스럽고 전문적인 느낌 |
| 포인트 색상 | 핑크 (`#ff7b8a`) | 블루 (`#3b82f6`) | Stripe, Vercel, Linear 등 실무 표준 |
| 배경색 | `#f8f5f2` (웜 베이지) | `#f1f5f9` (쿨 그레이) | 가독성과 눈의 피로도 개선 |
| 버튼 | 핑크 버튼 + 위로 튀어오르는 효과 | 블루 버튼, 조용한 hover | 실무 UI는 과도한 애니메이션 지양 |
| 사이드바 | 기본 Django 스타일 | 다크 네이비로 통일 | 헤더와 사이드바 색상 일관성 |
| 이모지 | 브랜딩에 이모지 사용 | 텍스트만 | 전문적인 느낌 |

---

### `index.html` — 관리자 대시보드 (첫 화면)

**역할:** `/admin/` 접속 시 처음 보이는 화면. 등록된 모든 모델 목록을 앱별로 정리하여 카드 형태로 표시.

**왜 이렇게 만들었는가?**

Django의 기본 대시보드는 단순한 텍스트 목록입니다. 우리는 이를 카드 그리드로 재구성하여:
- 어떤 모델이 있는지 한눈에 파악 가능
- "목록 보기"와 "추가" 버튼을 명확하게 분리
- 앱별 섹션 구분으로 탐색 편의성 향상

**화면에 표시되는 것:**
- `app_list` — Django가 자동으로 넘겨주는 등록된 앱·모델 목록
- `recent_actions` — 최근에 누가 어떤 데이터를 수정했는지 이력

---

### `chat/admin.py` — Chat 앱 모델 관리 설정

**역할:** Chat 앱의 모델들이 관리자 페이지에 어떻게 보일지 정의

**등록된 모델 목록:**

| 모델 | 관리자 표시명 | 주요 기능 |
|---|---|---|
| `Message` | Messages | 채팅 메시지 목록, 내용 50자 미리보기 |
| `ChatMemory` | Chat Memories | 대화 세션 요약 목록, 40자 미리보기 |
| `HariKnowledge` | HARI Knowledge | 하리 성격·지식 관리, 카테고리/키/값 검색 |
| `UserPersona` | User Personas | 사용자별 페르소나 데이터 |
| `GeneratedContent` | Generated Contents | AI 생성 콘텐츠, 발행 상태 필터 |
| `VisitLog` | Visit Logs | 방문 기록 |

**`verbose_name_plural` 수동 설정 이유:**
Django는 모델 이름에 자동으로 's'를 붙여 복수형을 만드는데,
`ChatMemory` → `Chat Memorys` (틀림), `HyperMemory` → `Hyper Memorys` (틀림)처럼
불규칙 복수형을 잘못 처리합니다.
`Model._meta.verbose_name_plural`을 직접 지정하여 올바른 복수형(Memories)으로 고쳤습니다.

---

### `rpg/admin.py` — RPG 앱 모델 관리 설정

**역할:** RPG 게임 관련 모델들의 관리자 설정

**등록된 모델 목록:**

| 모델 | 설명 |
|---|---|
| `Lorebook` | 게임 세계관, 배경 설정 |
| `Session` | 사용자별 게임 진행 세션 |
| `StoryProgress` | 챕터별 진행도 |
| `ChatLog` | 게임 내 대화 기록 |
| `MessageEmbedding` | 벡터 임베딩 데이터 |
| `HyperMemory` | 게임 핵심 사건 메모리 |
| `CharacterImage` | 캐릭터 이미지 |

---

## 5. 기능별 사용법

### 데이터 목록 보기
1. 대시보드에서 원하는 모델 카드의 **"목록 보기"** 클릭
2. 전체 데이터가 테이블 형태로 표시
3. 상단 검색창에서 검색, 오른쪽 필터로 조건 걸기 가능

### 데이터 추가
1. 대시보드에서 모델 카드의 **"추가"** 클릭
2. 또는 목록 페이지 우상단의 **"추가"** 버튼 클릭
3. 폼 작성 후 저장

### 데이터 수정
1. 목록에서 수정할 항목 클릭
2. 수정 폼에서 값 변경
3. **"저장"** 클릭

### 데이터 삭제
1. 목록에서 항목 옆 체크박스 선택
2. 하단 드롭다운에서 **"선택된 항목 삭제"** 선택
3. 또는 항목 상세 페이지에서 **"삭제"** 버튼 클릭
4. 확인 화면에서 최종 확인

### 하리 지식 수정 (가장 자주 할 작업)
1. 대시보드 → **"HARI Knowledge"** → 목록 보기
2. 수정할 지식 항목 클릭
3. `trait_value` 값을 원하는 내용으로 수정
4. `is_active` 체크박스로 활성/비활성 전환
5. 저장

### 사용자 Staff 권한 부여
1. 대시보드 → **"Users"** → 목록 보기
2. 해당 사용자 클릭
3. **"Staff status"** 체크박스 활성화
4. 저장
5. 해당 사용자는 이제 `/admin/` 접속 가능

---

## 6. 디자인 커스터마이징 방법

### 색상 변경
`base_site.html` 상단의 `:root { }` 안에서 CSS 변수만 바꾸면 됩니다.

```css
:root {
  --accent:      #3b82f6;  /* 포인트 색상 (버튼, 링크 등) */
  --accent-dark: #2563eb;  /* 포인트 색상 hover 시 */
  --header-bg:   #0f172a;  /* 헤더·사이드바 배경 */
  --bg:          #f1f5f9;  /* 전체 페이지 배경 */
  --surface:     #ffffff;  /* 카드·테이블 배경 */
  --border:      #e2e8f0;  /* 테두리 색상 */
}
```

예: 포인트 색상을 보라색으로 바꾸고 싶으면
```css
--accent:      #8b5cf6;
--accent-dark: #7c3aed;
```

### 대시보드 레이아웃 변경
`index.html`의 `.model-grid` CSS에서 카드 크기와 열 수를 조절합니다.
```css
.model-grid {
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  /* minmax의 첫 번째 값을 키우면 카드가 커지고 열 수가 줄어듦 */
}
```

### 새 모델을 관리자 페이지에 추가
해당 앱의 `admin.py`에 아래 형태로 추가합니다.
```python
from django.contrib import admin
from .models import 새모델

@admin.register(새모델)
class 새모델Admin(admin.ModelAdmin):
    list_display = ('id', '표시할필드1', '표시할필드2')
    search_fields = ('검색할필드',)
    list_filter = ('필터할필드',)
```
이것만 추가하면 관리자 대시보드에 자동으로 카드가 생깁니다.

---

## 7. 자주 하는 작업

### 하리 성격/지식 업데이트
```
/admin/ → HARI Knowledge → 수정할 항목 클릭 → trait_value 수정 → 저장
```

### 특정 사용자 비활성화
```
/admin/ → Users → 해당 사용자 클릭 → "Active" 체크 해제 → 저장
```

### 생성된 콘텐츠 발행 처리
```
/admin/ → Generated Contents → 해당 콘텐츠 클릭 → is_published 체크 → 저장
```

### 채팅 메시지 검색
```
/admin/ → Messages → 상단 검색창에 사용자명 또는 내용 입력
```

### 게임 세션 확인
```
/admin/ → Sessions → 목록에서 사용자별 진행 상황 확인
```

---

## 8. 주의사항

### 절대 하지 말아야 할 것

| 행동 | 이유 |
|---|---|
| `Message` 대량 삭제 | 복구 불가능, 사용자 데이터 영구 소실 |
| `HyperMemory` 무단 삭제 | RPG 게임 진행 데이터 손실 |
| `MessageEmbedding` 수동 수정 | 벡터 데이터 구조 깨짐, AI 검색 기능 오류 |
| superuser 계정 비밀번호 공유 | 보안 사고 위험 |
| `UserPersona` 일괄 삭제 | 사용자별 맞춤 데이터 전부 소실 |

### staff 계정 vs superuser 계정

| 구분 | 접근 범위 | 권한 변경 |
|---|---|---|
| **superuser** | 모든 모델, 모든 기능 | 다른 사용자 권한도 변경 가능 |
| **staff** | admin.py에서 허용한 모델만 | 자기 자신 권한 변경 불가 |

실무에서는 팀원에게 superuser를 주지 않고 staff + 필요한 모델 권한만 부여하는 것이 원칙입니다.

### 데이터 수정 전 확인 습관
- 수정 전 현재 값을 메모해두기
- 대량 작업(일괄 삭제 등)은 팀원과 상의 후 진행
- 서버 DB는 로컬 DB와 다름 — 로컬에서 테스트 후 서버에 반영

---

---

## 9. 계획 중인 기능 (백엔드 작업 대기)

> `BACKEND_REQUEST.md` (2026-04-10) 에 상세 요청서 작성 완료.
> `chat/admin.py` 하단에 활성화 코드가 주석으로 준비되어 있음.
> 백엔드 팀이 모델을 생성하면 **주석 해제만으로 즉시 admin에 반영**된다.

### 추가될 5개 기능

| 기능 | 모델 | 현재 상태 | 활성화 조건 |
|---|---|---|---|
| 갤러리 이미지 관리 | `GalleryImage` | HTML 하드코딩 | 모델 생성 후 주석 해제 |
| 뉴스/이벤트 관리 | `NewsEvent` | HTML 하드코딩 | 모델 생성 후 주석 해제 |
| 문의 폼 접수 내역 | `ContactSubmission` | DB 저장 안 됨 | 모델 생성 + views.py 수정 후 주석 해제 |
| YouTube 영상 관리 | `VideoContent` | HTML 하드코딩 | 모델 생성 후 주석 해제 |
| 멤버십 구독 현황 | `UserMembership` | 모델 없음 | 모델 생성 후 주석 해제 |

### 활성화 방법 (백엔드 모델 생성 후)

```python
# backend/chat/admin.py 하단에서 아래 주석 해제

# from .models import (
#     GalleryImage, NewsEvent, ContactSubmission, VideoContent, UserMembership,
# )
# @admin.register(GalleryImage) ...
# @admin.register(NewsEvent) ...
# @admin.register(ContactSubmission) ...
# @admin.register(VideoContent) ...
# @admin.register(UserMembership) ...
```

### 각 기능 설명

**갤러리 이미지 관리**
- admin 목록에서 이미지 URL, 캡션, 순서, 노출 여부를 한 화면에서 수정 가능
- `list_editable` 설정으로 목록에서 바로 저장 (상세 페이지 안 들어가도 됨)

**뉴스/이벤트 관리**
- 제목, 날짜, 상태(예정/진행중/완료/미정), 노출 여부 관리
- 필터로 예정 행사만, 지난 행사만 빠르게 구분 가능

**문의 폼 접수 내역**
- 사이트에서 제출된 문의를 admin에서 조회
- `is_read` 필드로 확인/미확인 관리
- 읽기 전용 (내용 수정 불가, 조회·삭제만 가능)

**YouTube 영상 관리**
- 영상 URL, 제목, 순서, 노출 여부 관리
- 목록에서 바로 순서 변경 가능

**멤버십 구독 현황**
- 사용자별 플랜(Free/Fan+/VIP), 포인트, 만료일 관리
- admin에서 특정 사용자에게 VIP 부여, 포인트 지급 가능
- 목록에서 바로 플랜·포인트 수정 가능

---

## 부록: 파일 수정 권한

| 파일 | 수정 가능 여부 | 담당 |
|---|---|---|
| `templates/admin/base_site.html` | 자유롭게 | 프론트엔드 |
| `templates/admin/index.html` | 자유롭게 | 프론트엔드 |
| `templates/admin/change_list.html` | 자유롭게 | 프론트엔드 |
| `templates/admin/change_form.html` | 자유롭게 | 프론트엔드 |
| `chat/admin.py` | 승인 후 | 백엔드 협의 |
| `rpg/admin.py` | 승인 후 | 백엔드 협의 |
| `chat/models.py` | 절대 금지 | — |
| `rpg/models.py` | 절대 금지 | — |
