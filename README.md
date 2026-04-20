# 🎥 HARI: The AI Virtual Influencer
> **"AI 에이전트 시대, 팬 경험을 스케일링하는 새로운 테크 크리에이터"**

<p align="center">
  <a href="https://linktr.ee/chatting_hari">
    <img src="https://img.shields.io/badge/Linktree-하리_공식_링크-39E09B?style=for-the-badge&logo=linktree&logoColor=white" alt="HARI Linktree"/>
  </a>
</p>

<p align="center">
  <img width="1024" height="1024" alt="Image" src="https://github.com/user-attachments/assets/19d961a5-22cc-4c22-84a7-677388c86e5f" />
</p>

---

## 0. Project Overview
**하리(HARI)**는 단순한 정보 전달용 챗봇을 넘어, 사용자 전용 '페르소나'를 가진 테크 전문 가상 인플루언서 플랫폼입니다. AI 에이전트 시대를 맞아, 1:1 대화, 실시간 음성 스트리밍, SNS 콘텐츠 자동 생성을 통해 사용자에게 실존하는 셀럽과의 교감(Parasocial Interaction)을 제공합니다.

* **진행 기간:** 2026.03.04 ~ 2026.04.24 (SK네트웍스 Family AI 22기)
* **공식 링크:** [하리 링크트리 바로가기](https://linktr.ee/chatting_hari)
* **핵심 가치:** 단방향 콘텐츠 소비에서 벗어난 일상 속 '과몰입' 상호작용 구현

---

## 1. Key Features
* **💬 1:1 Private Chat:** 유저별 맥락을 기억(Memory)하고 실시간 음성(TTS)으로 대답하는 개인화 채팅.
* **🎬 Auto-Content Pipeline:** 최신 테크 트렌드를 분석하여 숏폼 영상과 SNS 피드를 자동으로 생성 및 업로드.
* **👤 Consistent Persona:** LoRA 학습을 통한 외형 일관성 유지 및 고유의 말투/취향(Preference) 반영.
* **🛒 Point Shop:** 활동 점수를 통한 굿즈 구매 및 멤버십 전용 콘텐츠 제공.

---

## 2. Tech Stack

### AI Modeling
* **LLM:** LangChain, LangGraph (Multi-turn 대화 및 가드레일 제어)
* **Voice:** GPT-SoVITS v4 (성우 데이터 기반 고정밀 음색 복제)
* **Vision:** Z-Image-turbo(이미지 생성), AI-toolkit(LoRA 학습), Heygen API (영상 생성)
* **Preprocessing:** Pandas, Seedvr2 (이미지 업스케일링), Z-image-Turbo

### Infrastructure & Backend
* **Servers:** AWS (EC2, Elastic Beanstalk), Runpod (RTX 5090 GPU 인스턴스)
* **Frameworks:** Django, FastAPI (WebSockets 실시간 통신)
* **Automation:** n8n, Playwright CUA (SNS 스크래핑), Celery & Redis (작업 큐 관리)
* **Database:** PostgreSQL (유저 및 페르소나 데이터, Vector DB, RAG 지식 검색)

---

## 3. System Architecture

<p align="center">
  <img width="3840" height="1680" alt="Image" src="https://github.com/user-attachments/assets/0e7b97a3-f3d0-487d-9157-e485a5109137" />
</p>

위 아키텍처 다이어그램은 하리 플랫폼의 전체적인 데이터 흐름과 컴포넌트 간 상호작용을 시각화합니다.
1. **Automation Pipeline (AWS Cloud 1):** SNS 트렌드 분석 및 대본 생성, 영상 제작 오케스트레이션.
2. **Web Server (AWS Cloud 2):** Django 기반의 서비스 로직 및 LangChain을 활용한 대화 엔진 구동.
3. **GPU Instance (Runpod):** 이미지 생성 및 TTS 추론 등 고부하 연산 전담.
4. **Database Layer:** 유저별 대화 이력 및 하리의 페르소나 벡터값 저장/조회.

---

## 4. Data Preprocessing & Training
* **TTS Data:** 전문 성우 녹음본 40문장 정제 (**LSD 9.27, Similarity 0.9636** 확보)
* **Persona Data:** 놉크릭 버번, 테크 트렌드 등 구체적인 취향 데이터를 수기 구축하여 RAG 시스템에 이식.
* **Image Data:** 캐릭터 일관성을 위해 고유 LoRA 가중치 모델(`safetensors`) 제작.

---

## 5. Getting Started

### Prerequisites
* Python 3.10+
* NVIDIA GPU (VRAM 16GB+ 권장)
* AWS & OpenAI API Keys

### Installation
```bash
# Repository 클론
git clone [https://github.com/skn-ai22-251029/SKN22-Final-4Team-Web.git](https://github.com/skn-ai22-251029/SKN22-Final-4Team-Web.git)

# 백엔드 디렉토리 이동 및 패키지 설치
cd SKN22-Final-4Team-Web/backend
pip install -r requirements.txt

# 서버 실행 (Django)
python manage.py runserver
```

---

## 6. Project Structure

현재 레포지토리의 상세 디렉토리 구조입니다.

```
SKN22-Final-4Team-WEB/
│
├── .github/
│   └── workflows/
│       └── deploy-eb.yml          # GitHub Actions: develop 브랜치 push 시 EB 자동 배포
│
├── backend/                       # 🔑 배포 대상 루트 (EB에 이 폴더 전체를 zip으로 패키징)
│   │
│   ├── config/                    # Django 프로젝트 설정
│   │   ├── settings.py            # 환경 변수, DB, 인증, static 경로 등 전체 설정
│   │   ├── urls.py                # 루트 URL 라우터
│   │   ├── asgi.py                # ASGI 엔트리포인트 (WebSocket + HTTP)
│   │   └── wsgi.py                # WSGI 엔트리포인트
│   │
│   ├── chat/                      # 핵심 Django 앱 (채팅 기능 + 프론트엔드 뷰 통합)
│   │   ├── views.py               # 모든 페이지 뷰 함수 (homepage, mypage, chat 포함)
│   │   ├── models.py              # Message, ChatMemory DB 모델
│   │   ├── consumers.py           # WebSocket Consumer (Django Channels)
│   │   ├── engine.py              # LangChain 기반 대화 엔진 (하리 페르소나 + 메모리)
│   │   ├── serializers.py         # DRF 직렬화기
│   │   ├── urls.py                # /api/chat/ 하위 API URL
│   │   ├── routing.py             # WebSocket URL 라우팅
│   │   └── static/chat/           # 채팅 전용 정적 파일
│   │
│   ├── accounts/                  # 유저 계정 앱 (allauth·dj-rest-auth 확장용)
│   │
│   ├── templates/                 # Django 템플릿 루트
│   │   └── frontend/              # 하리 프론트엔드 HTML 템플릿
│   │       ├── homepage.html      # 홈페이지 (랜딩 · 갤러리 · 뉴스 · 멤버십)
│   │       ├── mypage.html       # 팬클럽 대시보드 (랭킹 · 샵 · 프로필)
│   │       ├── chat.html          # 하리 채팅 UI (단독 페이지)
│   │       └── includes/          # 페이지별 분리된 섹션 컴포넌트
│   │           ├── homepage/
│   │           │   ├── _nav_auth.html       # 내비게이션 + 인증 모달
│   │           │   ├── _s1_hero.html        # Hero 섹션
│   │           │   ├── _s2_profile.html     # 프로필 섹션
│   │           │   ├── _s3_gallery.html     # 갤러리 섹션
│   │           │   ├── _s4_chat.html        # 채팅 미리보기 섹션
│   │           │   ├── _s5_news.html        # 뉴스·유튜브 쇼츠 섹션
│   │           │   ├── _s6_membership.html  # 멤버십 CTA 섹션
│   │           │   ├── _s7_contact.html     # 문의 섹션
│   │           │   └── _s8_footer.html      # 푸터
│   │           ├── mypage/
│   │           │   ├── _topbar.html         # 상단 바
│   │           │   ├── _sidebar.html        # 사이드 내비게이션
│   │           │   ├── _profile.html        # 유저 프로필 카드
│   │           │   ├── _ranking.html        # 팬 랭킹 테이블
│   │           │   ├── _shop.html           # 포인트 샵
│   │           │   ├── _myinfo.html         # 내 정보 · 설정
│   │           │   └── _buymodal.html       # 구매 확인 모달
│   │           └── chat/
│   │               ├── _header.html         # 채팅 헤더
│   │               ├── _messages.html       # 메시지 목록
│   │               ├── _input.html          # 메시지 입력창
│   │               ├── _quickreply.html     # 빠른 답장 버튼
│   │               ├── _search.html         # 대화 검색 모달
│   │               └── _emoji.html          # 이모지 패널
│   │
│   ├── static/                    # 공유 정적 파일 (collectstatic 소스)
│   │   ├── css/                   # 전역 CSS
│   │   ├── js/                    # 전역 JavaScript
│   │   ├── images/                # 하리 이미지 (hari_image1.png ~ hari_logo.png)
│   │   └── video/                 # 하리 쇼츠 영상 (video_20260313.mp4 등)
│   │
│   ├── staticfiles/               # collectstatic 결과물 (자동 생성·배포 시 사용)
│   ├── media/                     # 유저 업로드 파일
│   ├── manage.py                  # Django 관리 CLI
│   ├── requirements.txt           # Python 패키지 목록
│   ├── Procfile                   # EB 프로세스 정의 (migrate → collectstatic → daphne)
│   ├── Dockerfile                 # Docker 이미지 정의
│   └── docker-compose.yml         # 로컬 Docker 환경
│
├── ai-influencer/                 # AI 콘텐츠 자동화 파이프라인 (n8n, 대본 생성 등)
├── heygen_pipeline/               # HeyGen API 영상 생성 파이프라인
├── img_gen/                       # 이미지 생성 (Z-Image-turbo, LoRA)
├── langchain-skills/              # LangChain 실험·스킬 모듈
├── langsmith-skills/              # LangSmith 트레이싱·평가
└── notebooklm/                    # NotebookLM 연동 실험
```

---

## 7. URL Routing

| URL 경로 | 뷰 함수 | 설명 |
|---|---|---|
| `/` | `chat_index` | 채팅 메인 (로그인 필요) |
| `/homepage/` | `homepage` | 하리 랜딩 홈페이지 |
| `/mypage/` | `mypage` | 팬클럽 대시보드 |
| `/hari-chat/` | `frontend_chat` | 하리 채팅 전용 UI |
| `/health/` | `health_check` | 서버 헬스체크 (EB 모니터링) |
| `/admin/` | Django Admin | 관리자 페이지 |
| `/accounts/` | allauth | 소셜 로그인 (Google, Naver) |
| `/api/auth/` | dj-rest-auth | JWT 인증 API |
| `/api/chat/` | chat.urls | 채팅 메시지 REST API |
| `ws://.../ws/chat/` | WebSocket | 실시간 채팅 (Django Channels) |

---

## 8. Deployment (AWS Elastic Beanstalk)

```
develop 브랜치 push
    ↓
GitHub Actions (.github/workflows/deploy-eb.yml)
    ↓
backend/ 폴더 → deploy.zip 패키징
    ↓
AWS Elastic Beanstalk 배포
    ↓
Procfile 실행:
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput   ← static/ → staticfiles/ 복사
  daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

### 환경 변수 (`.env` / EB 환경 설정)
| 변수명 | 설명 |
|---|---|
| `SECRET_KEY` | Django 시크릿 키 |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `GOOGLE_CLIENT_ID` | 구글 소셜 로그인 |
| `GOOGLE_CLIENT_SECRET` | 구글 소셜 로그인 시크릿 |
| `NAVER_CLIENT_ID` | 네이버 소셜 로그인 |
| `NAVER_CLIENT_SECRET` | 네이버 소셜 로그인 시크릿 |
| `DB_HOST` / `RDS_HOSTNAME` | PostgreSQL 호스트 |
| `DB_NAME` / `RDS_DB_NAME` | DB 이름 |
| `REDIS_HOST` | Redis 호스트 (WebSocket Channel Layer) |

---

## 9. Team Members (SKN22-Final-4Team)

| 사진 | 이름 | 역할 | 주요 업무 |
| :---: | :--- | :--- | :--- |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/17c43ef6-fbc6-484e-9fe2-09b365c283d1" /> | **최민호** | **PM** | PM, BM 개발, 시장 조사, 데이터 수집 총괄 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/28447344-fbb5-4f26-90bb-11ad3a8fd477" /> | **박준석** | **Creative** | 세계관 구축, UI/UX 설계, 데이터 수집 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/71c56c29-1306-4cd4-9fe3-78c1b7942096" /> | **안민제** | **AI Lead** | TTS(GPT-SoVITS) 학습 및 생성, LLM TTS 스트리밍 설계 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/c9470eb1-95db-43b0-b8f0-0d953a559891" /> | **한승혁** | **Infra** | 클라우드 서버 관리, 이미지/영상 학습 및 생성 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/05847c89-5f59-4184-81b3-355e85a85fa5" /> | **엄형은** | **Contents** | 대본 생성 자동화, 콘텐츠 생성-업로드 파이프라인 구축 |

---

## 10. License

본 프로젝트는 **SK네트웍스 Family AI 22기** 교육 과정의 일환으로 제작되었으며, 모든 권리는 **SKN22-Final-4Team**에 있습니다.
