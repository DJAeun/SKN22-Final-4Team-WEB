# 🎥 HARI: The AI Virtual Influencer
> **"AI 에이전트 시대, 팬 경험을 스케일링하는 새로운 테크 크리에이터"**

<p align="center">
  <a href="https://linktr.ee/chatting_hari">
    <img src="https://img.shields.io/badge/Linktree-하리_공식_링크-39E09B?style=for-the-badge&logo=linktree&logoColor=white" alt="HARI Linktree"/>
  </a>
</p>

<p align="center">
  <img width="1920" height="800" alt="33633563980734-1" src="https://github.com/user-attachments/assets/1bfbeded-425e-4589-9dd7-eab0fce49be2" />
</p>

---

## 0. Project Overview
**하리(HARI)**는 단순한 정보 전달용 챗봇을 넘어, 그녀만의 '페르소나'를 가진 테크 전문 가상 인플루언서 플랫폼입니다. AI 에이전트 시대를 맞아, SNS 콘텐츠 자동 생성, 1:1 대화, 실시간 음성 스트리밍, 몰입형 롤플레잉 게임을 통해 사용자에게 실존하는 셀럽과의 교감(Parasocial Interaction)을 제공합니다.

* **진행 기간:** 2026.03.04 ~ 2026.04.24 (SK네트웍스 Family AI 22기)
* **공식 링크:** [하리 링크트리 바로가기](https://linktr.ee/chatting_hari)
* **핵심 가치:** 단방향 콘텐츠 소비에서 벗어난 일상 속 '과몰입' 상호작용 구현

---

## 1. Key Features
* **💬 1:1 Private Chat:** 유저별 맥락을 기억(Memory)하고 실시간 음성(TTS)으로 대답하는 개인화 채팅.
* **🎬 Auto-Content Pipeline:** 최신 테크 트렌드를 분석하여 숏폼 영상과 SNS 피드를 자동으로 생성 및 업로드.
* **👤 Consistent Persona:** LoRA 학습을 통한 외형 일관성 유지 및 고유의 말투/취향(Preference) 반영.
* **📖 Roleplaying Game:** 몰입형 롤플레잉 게임을 통한 재미와 교감.

---

## 2. Tech Stack

<table align="center">
  <tr>
    <td align="center" width="220">
      <strong>Frontend</strong><br/><br/>
      <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React"/>
      <img src="https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite"/>
      <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" alt="Tailwind CSS"/>
    </td>
    <td align="center" width="220">
      <strong>Backend</strong><br/><br/>
      <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django"/>
      <img src="https://img.shields.io/badge/Django_REST_Framework-A30000?style=for-the-badge&logo=django&logoColor=white" alt="Django REST Framework"/>
      <img src="https://img.shields.io/badge/Channels-FF6F00?style=for-the-badge&logo=websocket&logoColor=white" alt="Django Channels"/>
    </td>
    <td align="center" width="220">
      <strong>AI / LLM</strong><br/><br/>
      <img src="https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=chainlink&logoColor=white" alt="LangChain"/>
      <img src="https://img.shields.io/badge/LangGraph-4B5563?style=for-the-badge&logo=graphql&logoColor=white" alt="LangGraph"/>
      <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI"/>
    </td>
  </tr>
  <tr>
    <td align="center" width="220">
      <strong>Data</strong><br/><br/>
      <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
      <img src="https://img.shields.io/badge/pgvector-336791?style=for-the-badge&logo=postgresql&logoColor=white" alt="pgvector"/>
      <img src="https://img.shields.io/badge/ChromaDB-7B61FF?style=for-the-badge&logo=databricks&logoColor=white" alt="ChromaDB"/>
    </td>
    <td align="center" width="220">
      <strong>Async / Realtime</strong><br/><br/>
      <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
      <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery"/>
      <img src="https://img.shields.io/badge/WebSocket-010101?style=for-the-badge&logo=socketdotio&logoColor=white" alt="WebSocket"/>
    </td>
    <td align="center" width="220">
      <strong>Infra / DevOps</strong><br/><br/>
      <img src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=FF9900" alt="AWS"/>
      <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
      <img src="https://img.shields.io/badge/Runpod-5B21B6?style=for-the-badge&logo=nvidia&logoColor=white" alt="Runpod"/>
    </td>
  </tr>
</table>

### AI Modeling
* **LLM:** LangChain, LangGraph (Multi-turn 대화 및 가드레일 제어)
* **Voice:** GPT-SoVITS v4 (맞춤 성우 음성 기반 고정밀 음색 복제)
* **Vision:** Z-Image-turbo(이미지 생성), AI-toolkit(LoRA 학습), Heygen API (영상 생성)
* **Preprocessing:** Pandas, Seedvr2 (이미지 업스케일링), Z-image-Turbo

### Infrastructure & Backend
* **Servers:** AWS (EC2, Elastic Beanstalk), Runpod (RTX 5090 GPU 인스턴스)
* **Frameworks:** Django, FastAPI (WebSockets 실시간 통신)
* **Automation:** n8n, Playwright CUA (SNS 스크래핑), Celery & Redis (작업 큐 관리)
* **Database:** PostgreSQL (유저 및 페르소나 데이터, Vector DB, RAG 지식 검색)

---

## 3. System Architecture

<img width="1899" height="1124" alt="readme1" src="https://github.com/user-attachments/assets/c163086b-28a9-4314-bc9b-149e5b994505" />
<img width="2372" height="914" alt="1e18e22572cb9603" src="https://github.com/user-attachments/assets/17a6de64-eadd-41e5-8758-162a87804746" />
<img width="2372" height="1062" alt="7f66dae7009ab4f9" src="https://github.com/user-attachments/assets/5d53aac9-451a-4e20-a33b-87dc156bfe80" />

---

## 4. Prompt Architecture
하리의 롤플레잉 엔진은 단일 지시문이 아니라, **규칙 주입 → 장면 생성 → 자기 검수 → 최종 출력**으로 이어지는 프롬프트 샌드위치 구조로 설계되었습니다. 이를 통해 캐릭터 일관성, 서사 몰입감, 출력 안정성을 동시에 확보했습니다.

* **Outer Guardrail Layer:** 세계관, 시점, 문체, 금지 규칙, 시공간 표기, 유저 행동 처리 원칙을 상단 프롬프트에 고정해 캐릭터 붕괴와 메타 발화를 방지.
* **Scene Composition Layer:** `Prologue`, `Past Records`, `Recent Records`, `Starting Point`, `Current Portrait`를 함께 주입해 장면 맥락과 감정선, 초상 상태를 반영한 서사를 생성.
* **Self-Review Sandwich:** 모델이 `Planning → Draft → Review → Revision` 4단계를 거치며 초안을 스스로 점검한 뒤, 최종 `Revision`만 사용자에게 노출하도록 구성.
* **Portrait Transition Control:** 장면 중 하리의 표정이나 복장이 의미 있게 바뀌는 순간에만 `<img="clothes_emotion">` 명령을 삽입해 텍스트 서사와 캐릭터 이미지 전환을 동기화.

---

## 5. Data Preprocessing & Training
* **TTS Data:** 전문 성우 녹음본 40문장 정제 (**LSD 9.27, Similarity 0.9636** 확보)
* **Image Data:** 캐릭터 일관성을 위해 고유 LoRA 가중치 모델(`safetensors`) 제작.
* **Trend Data Pipeline:** 최신 테크 뉴스·웹 문서를 조건부로 수집(Tavily Web Search)하고, 핵심 정보를 요약·정제해 영상 대본 생성의 근거 데이터로 활용.

---

## 6. Getting Started

### Prerequisites
* Python 3.10+
* NVIDIA GPU (VRAM 16GB+ 권장)
* AWS & OpenAI & Google Cloud API Keys

### Installation
```bash
# Repository 클론
git clone [https://github.com/skn-ai22-251029/SKN22-Final-4Team-Web.git](https://github.com/skn-ai22-251029/SKN22-Final-4Team-Web.git)

# 백엔드 디렉토리 이동 및 패키지 설치
cd SKN22-Final-4Team-Web/backend
pip install -r requirements.txt
```

### Run Server
```bash
cd backend
python manage.py runserver
```

---

## 7. Project Structure

현재 레포지토리의 상세 디렉토리 구조입니다.

```
SKN22-Final-4Team-WEB/
│
├── .github/
│   └── workflows/
│       └── deploy-eb.yml          # GitHub Actions: develop 브랜치 push 시 EB 자동 배포
│
├── backend/                       # 🔑 Django 백엔드 및 배포 대상 루트
│   │
│   ├── .ebextensions/             # AWS Elastic Beanstalk 환경 설정
│   ├── .platform/                 # EB 플랫폼 훅/런타임 설정
│   ├── config/                    # Django 프로젝트 설정
│   │   ├── settings.py            # 환경 변수, DB, 인증, 정적 파일 설정
│   │   ├── urls.py                # 루트 URL 라우터
│   │   ├── asgi.py                # ASGI 엔트리포인트 (HTTP + WebSocket)
│   │   └── celery.py              # Celery 앱 설정
│   │
│   ├── chat/                      # 하리 채팅 서비스 핵심 앱
│   │   ├── engine.py              # LangChain/LangGraph 기반 채팅 엔진
│   │   ├── consumers.py           # Django Channels WebSocket Consumer
│   │   ├── web_search.py          # 조건부 웹 검색(Tavily) 로직
│   │   ├── memory_extractor.py    # 대화 메모리 추출 및 저장
│   │   ├── memory_vector.py       # 벡터 검색/임베딩 연동
│   │   ├── models.py              # Message, ChatMemory 등 DB 모델
│   │   ├── views.py               # 홈페이지·채팅·마이페이지 뷰
│   │   └── management/commands/   # 콘텐츠 처리 관리 명령어
│   │
│   ├── roleplay/                  # 롤플레잉 엔진 및 프롬프트 시스템
│   │   ├── engine.py              # 롤플레잉 생성/파싱 엔진
│   │   ├── tasks.py               # 비동기 작업 처리
│   │   ├── prompts/               # 롤플레잉 프롬프트 템플릿
│   │   │   └── llm_rule.md        # Prompt Sandwich 핵심 규칙
│   │   ├── frontendexample/       # React + Vite 기반 롤플레잉 UI
│   │   └── templates/roleplay/    # 롤플레잉 템플릿
│   │
│   ├── rpg/                       # 롤플레잉 세션/로어북/이미지 모델 관리 앱
│   │   ├── models.py              # Session, Lorebook, CharacterImage 등
│   │   └── admin.py               # 관리자 페이지 커스터마이징
│   │
│   ├── templates/                 # Django 템플릿 루트
│   │   ├── frontend/              # 사용자용 페이지 템플릿
│   │   │   ├── homepage.html      # 랜딩 페이지 (Nav/Auth 모달 CSS 포함)
│   │   │   ├── chat.html          # 실시간 채팅 페이지
│   │   │   ├── mypage.html        # 마이페이지 (구독·계정 관리)
│   │   │   ├── abouthari.html     # 하리 소개 페이지 (프로필·SNS·갤러리 미리보기)
│   │   │   ├── gallery.html       # 갤러리 페이지 (카테고리 필터·라이트박스)
│   │   │   ├── video.html         # 영상 콘텐츠 페이지
│   │   │   ├── membership.html    # 멤버십 플랜 소개 페이지
│   │   │   └── includes/          # 각 페이지 안에 삽입되는 섹션 단위 파일 모음
│   │   │       ├── homepage/      # 네비게이션, 로그인/회원가입 모달, 히어로, 하리 소개, 갤러리, 영상, 푸터
│   │   │       ├── mypage/        # 상단바, 사이드바, 내 정보·구독·계정 섹션
│   │   │       └── chat/          # 채팅 헤더, 메시지 목록, 입력창, 검색
│   │   └── admin/                 # Django Admin 커스텀 템플릿
│   │
│   ├── static/                    # 정적 파일 소스
│   │   ├── images/                # 하리 이미지 및 로고
│   │   ├── js/                    # 전역 JavaScript
│   │   └── roleplay-app/          # 빌드된 롤플레잉 프론트 정적 자산
│   │
│   ├── media/                     # 업로드/생성 산출물 저장소
│   ├── manage.py                  # Django 관리 CLI
│   ├── requirements.txt           # Python 의존성
│   ├── Procfile                   # EB 프로세스 실행 정의
│   ├── Dockerfile                 # Docker 이미지 정의
│   └── docker-compose.yml         # 로컬 개발용 Docker 구성
│
├── db/                            # DB 초기화 및 pgvector 적재 스크립트
│   ├── setup_db_schema.py
│   ├── ingest_to_pgvector.py
│   └── setup_rds.ps1
│
├── eval/                          # 품질 평가 및 부하 테스트
│   ├── golden_dataset.json        # 평가용 골든 데이터셋
│   ├── judge_eval.py              # LLM-as-a-judge 평가 스크립트
│   ├── load_test.py               # WebSocket 부하 테스트
│   └── results/                   # 테스트 결과 JSON
│
├── heygen_pipeline/               # HeyGen 기반 영상 생성 파이프라인
│   ├── generate_video.py          # 오디오 업로드, 영상 생성, 자막 합성
│   └── input_audio/               # 입력 음성/스크립트 파일
│
├── img_gen/                       # 이미지 생성 워크플로우 및 실행 스크립트
│   ├── workflow/                  # ComfyUI/생성 워크플로우 JSON
│   └── run_workflow/              # 이미지 생성 실행 스크립트
│
├── ai-influencer/                 # 외부 연동 및 자동화 관련 자산
├── langchain-skills/              # LangChain 실험/스킬 자료
├── langsmith-skills/              # LangSmith 트레이싱/평가 자료
├── BACKEND_REQUEST.md             # 프론트-백엔드 협업 요청 문서
├── README.md                      # 메인 README
└── README2.md                     # 발표/문서 정리용 README 초안
```

---

## 8. URL Routing

| URL 경로 | 뷰 함수 | 설명 |
|---|---|---|
| `/` | `homepage` | 하리 랜딩 홈페이지 |
| `/homepage/` | `homepage` | 하리 메인 랜딩 페이지 |
| `/hari-chat/` | `frontend_chat` | 하리 실시간 채팅 UI |
| `/mypage/` | `mypage` | 팬 대시보드 (내 정보) |
| `/abouthari/` | `abouthari_page` | 하리 소개 페이지 |
| `/gallery/` | `gallery_page` | 이미지 갤러리 페이지 |
| `/video/` | `video_page` | 영상 콘텐츠 페이지 |
| `/membership/` | `membership_page` | 멤버십 소개 페이지 |
| `/contact/` | `contact_form` | 문의 제출 엔드포인트 (Footer 내 폼) |
| `/roleplay/` | `roleplay_page` | 롤플레잉 메인 페이지 |
| `/health/` | `health_check` | 서버 헬스체크 |
| `/admin/` | Django Admin | 관리자 페이지 |
| `/admin/dashboard-stats/` | `admin_stats_api` | 관리자 대시보드 통계 API |
| `/admin/youtube-stats/` | `youtube_stats_api` | YouTube 채널 통계 API |
| `/admin/youtube-analytics/` | `youtube_analytics_api` | YouTube Analytics API |
| `/admin/instagram-stats/` | `instagram_stats_api` | Instagram 통계 API |
| `/admin/tiktok-stats/` | `tiktok_stats_api` | TikTok 통계 API |
| `/accounts/` | allauth | 소셜 로그인/계정 관리 |
| `/api/auth/` | dj-rest-auth | 로그인/로그아웃/JWT 인증 API |
| `/api/auth/registration/` | `frontend_signup_view` + dj-rest-auth registration | 회원가입 처리 엔드포인트 |
| `/api/chat/` | `chat.urls` | 메시지/메모리 관련 REST API |
| `/api/roleplay/` | `roleplay.urls` | 롤플레잉 세션 REST API |
| `ws://.../ws/chat/` | `ChatConsumer` | 실시간 채팅 WebSocket |
| `ws://.../ws/chat/{session_id}/` | `ChatConsumer` | 세션 기반 채팅 WebSocket |
| `ws://.../ws/roleplay/{session_id}/` | `RoleplayConsumer` | 롤플레잉 WebSocket |

---

## 9. Deployment (AWS Elastic Beanstalk)

```
develop 브랜치 push
    ↓
GitHub Actions (.github/workflows/deploy-eb.yml)
    ↓
backend/ 폴더 → deploy.zip 패키징
    ↓
AWS Elastic Beanstalk 배포
    ↓
EB predeploy hook에서 환경변수 기반 .env 생성
    ↓
Docker Compose 서비스 기동
  - web: migrate → collectstatic → daphne
  - celery: 비동기 작업 처리
  - redis: channel layer / celery broker
    ↓
Nginx → Daphne reverse proxy 및 static/media 서빙
```

* **CI/CD:** `develop` 브랜치에 push되면 GitHub Actions가 `backend/`만 압축해 EB에 배포합니다.
* **Environment Injection:** EB 환경변수는 predeploy hook에서 `.env` 파일로 내려받아 컨테이너에서 사용합니다.
* **Runtime:** 실제 애플리케이션은 `docker-compose.yml` 기준으로 `web`, `celery`, `redis` 3개 서비스가 함께 동작합니다.
* **Web Serving:** `web` 컨테이너는 `migrate`, `collectstatic`, `daphne`를 순서대로 실행하고, Nginx가 80 포트에서 Daphne(8000)로 프록시합니다.

### 환경 변수 (`.env` / EB 환경 설정)
로컬 개발용 `.env` 파일은 [`backend/.env.example`](c:\Users\minje\Documents\SKN22-FINAL-4TEAM_WEB\backend\.env.example)을 복사해 생성합니다.

```bash
cd backend
cp .env.example .env
```


#### 필수 환경 변수

| 변수명 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `SECRET_KEY` | Django 시크릿 키 |
| `DB_HOST` / `RDS_HOSTNAME` | PostgreSQL 호스트 |
| `DB_NAME` / `RDS_DB_NAME` | DB 이름 |
| `DB_USER` | PostgreSQL 사용자명 |
| `DB_PASSWORD` | PostgreSQL 비밀번호 |
| `DB_PORT` | PostgreSQL 포트 |

#### 선택 환경 변수

| 변수명 | 설명 |
|---|---|
| `DJANGO_SECRET_KEY` | `docker-compose.yml`에서 `SECRET_KEY`로 전달할 때 사용하는 키 |
| `DEBUG` | 개발/운영 모드 설정 |
| `DB_SSLMODE` | PostgreSQL SSL 연결 옵션 |
| `GOOGLE_CLIENT_ID` | 구글 소셜 로그인 |
| `GOOGLE_CLIENT_SECRET` | 구글 소셜 로그인 시크릿 |
| `NAVER_CLIENT_ID` | 네이버 소셜 로그인 |
| `NAVER_CLIENT_SECRET` | 네이버 소셜 로그인 시크릿 |
| `TAVILY_API_KEY` | 최신 웹 검색 기반 응답/콘텐츠 생성에 사용 |
| `LANGCHAIN_API_KEY` | LangChain/LangSmith API 키 |
| `LANGCHAIN_PROJECT` | LangSmith 프로젝트 이름 |
| `LANGCHAIN_TRACING_V2` | LangSmith 추적 활성화 여부 |
| `REDIS_HOST` | Redis 호스트 (WebSocket Channel Layer / Celery) |
| `GOOGLE_API_KEY` | Google GenAI 연동 시 사용 |
| `EMAIL_HOST_USER` | 메일 발송 SMTP 계정 |
| `EMAIL_HOST_PASSWORD` | 메일 발송 SMTP 비밀번호 |
| `S3_BUCKET` | 스크립트/산출물 S3 버킷 |
| `HEYGEN_API_KEY` | HeyGen 영상 생성 API 키 |
| `YOUTUBE_API_KEY` | YouTube Data API v3 키 (영상/채널 정보 조회) |
| `YOUTUBE_CHANNEL_HANDLE` | YouTube 채널 핸들 (기본값: `Hari-o5m2r`) |
| `YOUTUBE_CLIENT_ID` | YouTube Analytics OAuth2 클라이언트 ID |
| `YOUTUBE_CLIENT_SECRET` | YouTube Analytics OAuth2 클라이언트 시크릿 |
| `INSTAGRAM_APP_ID` | Instagram Graph API 앱 ID |
| `INSTAGRAM_APP_SECRET` | Instagram Graph API 앱 시크릿 |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API 액세스 토큰 |
| `TIKTOK_CLIENT_KEY` | TikTok API 클라이언트 키 |
| `TIKTOK_CLIENT_SECRET` | TikTok API 클라이언트 시크릿 |

---

## 10. Team Members (SKN22-Final-4Team)

| 사진 | 이름 | 역할 | 주요 업무 |
| :---: | :--- | :--- | :--- |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/17c43ef6-fbc6-484e-9fe2-09b365c283d1" /> | **최민호** | **PM** | PM, BM 개발, 시장 조사, QA |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/28447344-fbb5-4f26-90bb-11ad3a8fd477" /> | **박준석** | **Frontend** | 기초 페르소나 구축, UI/UX 설계, 관리자 페이지 설계 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/71c56c29-1306-4cd4-9fe3-78c1b7942096" /> | **안민제** | **AI Lead** | TTS(GPT-SoVITS) 파인튜닝 및 추론 엔진, 롤플레잉 서비스 개발 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/c9470eb1-95db-43b0-b8f0-0d953a559891" /> | **한승혁** | **Backend** | 서버 관리, 이미지/영상 학습 및 생성, DB 총괄, 1:1 채팅 개발 |
| <img width="60" alt="Image" src="https://github.com/user-attachments/assets/05847c89-5f59-4184-81b3-355e85a85fa5" /> | **엄형은** | **Contents** | 대본 생성, 콘텐츠 생성-업로드 자동화 파이프라인 구축 |

---

## 11. License

이 프로젝트는 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.ko) 라이선스를 따릅니다.
- **비영리 목적으로만 사용 가능합니다.** (상업적 이용 금지)
- 사용 시 원작자 및 출처를 반드시 명시해야 합니다.
- 자유로운 복제, 배포 및 수정이 가능합니다.
