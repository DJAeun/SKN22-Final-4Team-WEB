# AI Influencer Automation Pipeline — Phase 1

Discord 기반 AI 인플루언서 자동화 파이프라인.

---

## 아키텍처 개요

```
[Discord 사용자] ──→ [discord-bot] ──→ [messenger-gateway] ──→ [n8n]
                                               │                   │
                                               ↓                   │
                                         [PostgreSQL]             ─┘
                                               ↑
                              [Discord API] ←── discord adapter
```

### 서비스 구성

| 서비스 | 역할 | 포트 |
|--------|------|------|
| `postgres` | 데이터 저장소 | 내부 5432 |
| `n8n` | 워크플로 엔진 | 5678 (외부) |
| `messenger-gateway` | 메신저 허브 API | 8080 (외부) |
| `discord-bot` | Discord WebSocket 연결 | 없음 |

---

## 사전 요구사항

- AWS EC2 t3.large (x86_64, Ubuntu 22.04 이상) 또는 동급 서버
- **Docker** + **Docker Compose v2.24+** 설치
- **Discord Bot Token** (Discord Developer Portal에서 발급)
  - Privileged Gateway Intents: **Message Content Intent** 활성화 필수
  - Bot Permissions: Send Messages, Read Message History, Add Reactions, Use Application Commands
- 인바운드 포트 오픈: **5678** (n8n), **8080** (messenger-gateway)

---

## 서버 초기 세팅 (최초 1회)

### 1. SSH 접속

```bash
ssh -i your-key.pem ubuntu@<서버-퍼블릭-IP>
```

### 2. Docker 설치

```bash
# 패키지 업데이트
sudo apt-get update && sudo apt-get upgrade -y

# Docker 공식 GPG 키 및 저장소 추가
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Docker 설치
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
newgrp docker
```

### 3. Docker Compose v2 설치

```bash
# x86_64 기준 (ARM이면 aarch64로 변경)
sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 \
  -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
# Docker Compose version v2.24.0
```

### 4. 코드 클론

```bash
# 저장소 전체 클론
git clone https://github.com/<org>/SKN22-Final-4Team-WEB.git
cd SKN22-Final-4Team-WEB/ai-influencer
```

---

## 배포 및 실행

### 5. 환경변수 설정

```bash
cp .env.example .env
nano .env   # 또는 vi .env
```

`.env` 파일은 .env.example 파일을 복사하여 사용해주세요.

### 6. 전체 서비스 빌드 및 기동

```bash
docker-compose up -d --build
```

상태 확인:

```bash
docker-compose ps
# 모든 서비스 State: Up 확인
```

로그 확인:

```bash
docker-compose logs -f               # 전체
docker-compose logs -f messenger-gateway
docker-compose logs -f discord-bot
docker-compose logs -f n8n
```

---

## n8n 워크플로 설정

### 7. n8n 접속 및 Postgres 크레덴셜 등록

1. 브라우저에서 `http://<서버-퍼블릭-IP>:5678` 접속
2. `.env`의 `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD`로 로그인
3. 좌측 메뉴 **Settings → Credentials → + New Credential → PostgreSQL** 선택
4. 아래 값 입력 후 **Save** (반드시 이름을 `pg-credentials`로 지정):

   | 항목 | 값 |
   |------|-----|
   | Name | `pg-credentials` |
   | Host | `postgres` |
   | Port | `5432` |
   | Database | `.env`의 `POSTGRES_DB` |
   | User | `.env`의 `POSTGRES_USER` |
   | Password | `.env`의 `POSTGRES_PASSWORD` |

### 8. 워크플로 임포트

1. 좌측 메뉴 **Workflows → + New Workflow**
2. 우상단 **⋮ (점 3개) → Import from file** 으로 아래 3개 파일을 각각 임포트:
   - `n8n/workflows/WF-01_input_receive.json`
   - `n8n/workflows/WF-04_confirm_request.json`
   - `n8n/workflows/WF-05_confirm_handler.json`
3. 각 워크플로의 **Postgres 노드** 클릭 → Credentials → `pg-credentials` 선택
4. 각 워크플로 우상단 **Active 토글 ON** → **Save**

> **워크플로 수정 시 재임포트 방법 (docker 재빌드 불필요):**
> ```bash
> git pull   # 로컬 변경사항 서버에 반영
> ```
> n8n UI에서 기존 워크플로 삭제 → 새 JSON 파일로 재임포트

---

## 헬스체크

```bash
# Gateway 상태
curl http://localhost:8080/health
# {"status":"ok","db":"connected","adapters":["discord"]}

# n8n 상태
curl http://localhost:5678/healthz
# {"status":"ok"}

# 컨테이너 상태
docker-compose ps

# Postgres DB 접속 확인
docker-compose exec postgres psql -U aiuser -d ai_influencer -c "SELECT COUNT(*) FROM jobs;"
```

---

## 업데이트 배포

코드/워크플로 변경 시:

```bash
cd ~/SKN22-Final-4Team-WEB/ai-influencer
git pull

# 코드 변경 (messenger-gateway, discord-bot) → 재빌드 필요
docker-compose up -d --build messenger-gateway discord-bot

# docker-compose.yml 또는 .env 변경 → 해당 서비스만 재시작
docker-compose up -d n8n

# 전체 재시작
docker-compose up -d --build
```

---

## Discord 봇 설정 (Discord Developer Portal)

1. [https://discord.com/developers/applications](https://discord.com/developers/applications) 접속
2. **New Application** 생성
3. **Bot** 탭 → **Reset Token** → 토큰 복사 → `.env`의 `DISCORD_BOT_TOKEN`에 입력
4. **Bot** 탭 → **Privileged Gateway Intents**
   - **MESSAGE CONTENT INTENT** 토글 활성화 (필수)
5. **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Permissions: `Send Messages`, `Read Message History`, `Add Reactions`
6. 생성된 URL로 봇을 서버에 초대

### Discord ID 확인 방법

Discord 설정 → **고급 → 개발자 모드** 활성화 후:
- **유저 ID**: 사용자 이름 우클릭 → **ID 복사**
- **채널 ID**: 채널명 우클릭 → **ID 복사**

---

## 테스트 시나리오

1. 허용된 채널에 콘셉트 텍스트 전송 (예: "20대 여성을 위한 재테크 팁 영상")
   → "✅ 요청이 접수되었습니다!" 메시지 확인
2. WF-01 자동 실행 → 컨펌 메시지 + `[✅ 승인하기] [✏️ 수정 지시]` 버튼 수신
3. **✅ 승인하기** 버튼 클릭 → "🚀 승인되었습니다!" + DB `status=APPROVED` 확인
4. **✏️ 수정 지시** 버튼 클릭 → "어떤 점을 수정할까요?" 수신
   → 수정 내용 입력 → 재작업 플로우(WF-01 재실행) 확인

---

## API 엔드포인트 (messenger-gateway)

모든 `/internal/*` 엔드포인트는 `X-Internal-Secret` 헤더 인증 필수.

| Method | Path | 호출자 | 설명 |
|--------|------|--------|------|
| `POST` | `/internal/message` | discord-bot | 사용자 메시지 수신 |
| `POST` | `/internal/send-confirm` | n8n WF-01/04 | 컨펌 메시지 전송 |
| `POST` | `/internal/confirm-action` | discord-bot | 버튼 클릭 이벤트 처리 |
| `POST` | `/internal/send-text` | n8n WF-05 | 일반 텍스트 전송 |
| `GET`  | `/health` | 모니터링 | 헬스체크 |

---

## 트러블슈팅

| 증상 | 확인 사항 |
|------|-----------|
| Discord 메시지 수신 안 됨 | Developer Portal → MESSAGE CONTENT INTENT 활성화 확인 |
| Gateway 401 응답 | `X-Internal-Secret` 값이 `.env`의 `GATEWAY_INTERNAL_SECRET`과 일치하는지 확인 |
| n8n Postgres 연결 실패 | `postgres` 컨테이너 healthy 상태 대기 (`docker-compose ps`) |
| n8n `$env.*` 접근 거부 | `docker-compose.yml`에 `N8N_BLOCK_ENV_ACCESS_IN_NODE: "false"` 추가 후 `docker-compose up -d n8n` |
| n8n 워크플로 import 오류 | 기존 워크플로 삭제 후 재임포트. Postgres 크레덴셜 재선택 필수 |
| n8n `http://IP:5678` 접속 불가 | EC2 보안그룹 인바운드 5678 포트 오픈 확인 |
| 봇이 모든 채널에서 응답 | `.env`에 `DISCORD_ALLOWED_CHANNEL_IDS` 추가 후 `docker-compose up -d --build discord-bot` |
| Gateway DB 연결 실패 | postgres healthcheck 통과 여부 및 환경변수 확인 |

---

## Phase 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| **Phase 1** | Discord 메신저 파이프라인 | ✅ 완료 |
| **Phase 2** | NotebookLM 연동 — 스크립트 자동 생성 | 예정 |
| **Phase 3** | ComfyUI 연동 — 영상 자동 생성 | 예정 |
| **Phase 4** | SNS 자동 업로드 (YouTube, Instagram, TikTok) | 예정 |
