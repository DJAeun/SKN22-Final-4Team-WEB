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
| `n8n` | 워크플로 엔진 | 내부 5678 |
| `messenger-gateway` | 메신저 허브 API | 8080 (외부) |
| `discord-bot` | Discord WebSocket 연결 | 없음 |

---

## 사전 요구사항

- Docker, Docker Compose 설치
- Oracle 서버에 도메인 또는 고정 IP
- **Discord Bot Token** (Discord Developer Portal에서 발급)
  - Privileged Gateway Intents: **Message Content Intent** 활성화 필수
  - Bot Permissions: Send Messages, Read Message History, Use Application Commands
- 포트 오픈: **8080**

---

## 설치 및 실행

### 1. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 모든 값을 채워넣는다
```

### 2. 서비스 기동

```bash
docker-compose up -d --build
```

### 3. n8n 워크플로 임포트

1. `http://서버IP:5678` 접속
2. Postgres 크레덴셜 등록 (이름: `pg-credentials`)
3. `n8n/workflows/` 내 3개 JSON 파일 임포트 후 **Active 토글 ON**
4. WF-01, WF-05 Webhook URL 복사 → `.env` 업데이트
5. `docker-compose restart messenger-gateway n8n`

### 4. 헬스체크

```bash
curl http://localhost:8080/health
# {"status":"ok","db":"connected","adapters":["discord"]}
```

---

## Discord 봇 설정 (Discord Developer Portal)

1. [https://discord.com/developers/applications](https://discord.com/developers/applications) 접속
2. **New Application** 생성
3. **Bot** 탭 → **Reset Token** → 토큰 복사 → `.env`의 `DISCORD_BOT_TOKEN`에 입력
4. **Bot** 탭 → **Privileged Gateway Intents**
   - **MESSAGE CONTENT INTENT** 토글 활성화 (필수)
5. **OAuth2** → **URL Generator**
   - Scopes: `bot`
   - Permissions: `Send Messages`, `Read Message History`, `Add Reactions`
6. 생성된 URL로 봇을 서버에 초대

### DISCORD_ALLOWED_USER_IDS 확인 방법

Discord 설정 → **고급** → **개발자 모드** 활성화 후,
사용자 이름 우클릭 → **ID 복사** (18자리 숫자).

---

## 테스트 시나리오

1. 봇이 있는 채널에 콘셉트 텍스트 전송 (예: "20대 여성을 위한 재테크 팁 영상")
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
| Gateway DB 연결 실패 | postgres healthcheck 통과 여부 및 환경변수 확인 |

---

## Phase 로드맵

| Phase | 내용 | 상태 |
|-------|------|------|
| **Phase 1** | Discord 메신저 파이프라인 | ✅ 완료 |
| **Phase 2** | NotebookLM 연동 — 스크립트 자동 생성 | 예정 |
| **Phase 3** | ComfyUI 연동 — 영상 자동 생성 | 예정 |
| **Phase 4** | SNS 자동 업로드 (YouTube, Instagram, TikTok) | 예정 |
