# Issue #18: NotebookLM 연동 및 스크립트 자동 생성 파이프라인 구체화

## 📋 할일 목록 (Phase 2)

### 1. NotebookLM 스크립트 고도화
- [ ] `generate_report.py` 및 `generate_shortform.py`의 출력 포맷 표준화 (JSON/Markdown)
- [ ] 에러 핸들링 보강 및 재시도 로직(Retry Logic) 최적화
- [ ] `auth_manager.py`를 통한 세션 유지 및 자동 갱신 기능 안정성 검증

### 2. n8n 워크플로 연동 (WF-01 ~ WF-05)
- [ ] `WF-01_input_receive` 워크플로의 Mock 데이터를 실제 NotebookLM 호출 노드로 교체
- [ ] NotebookLM 스크립트 실행을 위한 전용 'Execute Command' 노드 및 환경 설정
- [ ] 생성된 스크립트 데이터를 DB(`postgres`)에 실시간으로 반영하는 로직 구현

### 3. 메신저 게이트웨이 및 API 확장
- [ ] NotebookLM 작업 상태(Status)를 관리하기 위한 API 엔드포인트 추가
- [ ] 비동기 작업 처리를 위한 응답 지연 시간 최적화 및 타임아웃 처리
- [ ] Discord 봇을 통해 생성 완료 알림 및 스크립트 초안을 사용자에게 전송

### 4. 인프라 및 배포 설정
- [ ] Docker Compose 환경 내 Playwright/Chromium 실행을 위한 라이브러리 및 의존성 설치
- [ ] `.env` 파일 내 NotebookLM 필수 환경변수(`NOTEBOOK_URL`, `STUDIO_URL` 등) 정의 및 동기화
- [ ] 사용자별 세션 격리 및 로그 관리 프로세스 확립
