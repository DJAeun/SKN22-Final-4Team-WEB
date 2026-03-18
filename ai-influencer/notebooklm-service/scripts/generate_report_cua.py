import argparse
import base64
import json
import logging
import os
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("generate_report_cua")

DATA_DIR = Path(__file__).parent.parent / "data"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_state" / "browser_profile"

SYSTEM_PROMPT = """You are a browser automation assistant controlling a Chromium browser via Playwright.
Given a screenshot of the current browser state and a task, output a JSON action to perform.

Output ONLY valid JSON in one of these formats:

1. Click: {"action": "click", "x": <int>, "y": <int>, "reason": "<why>"}
2. Type: {"action": "type", "text": "<text to type>"}
3. Key: {"action": "key", "key": "<key name e.g. Enter, Tab>"}
4. Scroll: {"action": "scroll", "x": <int>, "y": <int>, "delta_y": <int>}
5. Wait: {"action": "wait", "ms": <milliseconds>}
6. Done: {"action": "done"}

Rules:
- Output ONLY the JSON object, no explanation.
- Use "done" only when the report is fully generated and visible on screen.
- Do NOT include report text in the done action — text will be extracted from the DOM automatically.
- If the report is still generating, use "wait".
- Coordinates must be within 1280x800 viewport.
"""

# NotebookLM 보고서 컨테이너 후보 셀렉터 (우선순위 순)
_REPORT_SELECTORS = [
    "ms-content-chunk",
    "[class*='output-text']",
    "[class*='StudioOutput']",
    "[class*='studio-output']",
    "[class*='generated-output']",
    "[class*='OutputContent']",
    ".ProseMirror",
    "[contenteditable='true']",
    "[class*='report-content']",
]


def _ensure_logged_in(page: Page) -> None:
    """Google 로그인이 필요한 경우 자동으로 로그인한다.
    GOOGLE_EMAIL / GOOGLE_PASSWORD 환경변수가 설정된 경우에만 동작."""
    email = os.environ.get("GOOGLE_EMAIL", "")
    password = os.environ.get("GOOGLE_PASSWORD", "")

    if not email or not password:
        logger.info("[login] GOOGLE_EMAIL/PASSWORD 미설정 — 자동 로그인 건너뜀")
        return

    # 로그인 페이지 여부 확인
    if "accounts.google.com" not in page.url and "signin" not in page.url:
        logger.info("[login] 이미 로그인됨 (url=%s)", page.url)
        return

    logger.info("[login] 로그인 페이지 감지 — 자동 로그인 시작")

    try:
        # 이메일 입력
        page.wait_for_selector("input[type='email']", timeout=15000)
        page.fill("input[type='email']", email)
        page.click("button:has-text('다음'), button:has-text('Next'), #identifierNext")
        logger.info("[login] 이메일 입력 완료")

        # 비밀번호 입력
        page.wait_for_selector("input[type='password']", timeout=15000)
        time.sleep(0.5)
        page.fill("input[type='password']", password)
        page.click("button:has-text('다음'), button:has-text('Next'), #passwordNext")
        logger.info("[login] 비밀번호 입력 완료")

        # NotebookLM 리디렉션 대기 (최대 30초)
        page.wait_for_url("**/notebooklm.google.com/**", timeout=30000)
        logger.info("[login] 로그인 성공 — url=%s", page.url)

    except Exception as e:
        logger.error("[login] 자동 로그인 실패: %s", e)
        logger.error("[login] 현재 URL: %s", page.url)
        raise RuntimeError(f"Google 자동 로그인 실패: {e}")


def _extract_report_from_dom(page) -> str:
    """DOM에서 보고서 텍스트를 직접 추출. GPT OCR 대신 Playwright 사용."""
    # 1단계: 특정 CSS 셀렉터 시도
    js = """
    (selectors) => {
        for (const sel of selectors) {
            const els = document.querySelectorAll(sel);
            if (els.length === 0) continue;
            const text = Array.from(els)
                .map(e => e.innerText.trim())
                .filter(t => t.length > 0)
                .join('\\n\\n');
            if (text.length > 100) return text;
        }
        return null;
    }
    """
    try:
        result = page.evaluate(js, _REPORT_SELECTORS)
        if result and len(result.strip()) > 100:
            logger.info("[CUA] DOM 셀렉터 추출 성공: %d chars", len(result))
            return result.strip()
    except Exception as e:
        logger.warning("[CUA] DOM 셀렉터 추출 실패: %s", e)

    # 2단계: body 전체 텍스트 + 다중 패턴 파싱
    try:
        body_text = page.inner_text("body")
        logger.info("[CUA] body 텍스트 획득: %d chars", len(body_text))

        # 패턴 A: 스튜디오 패널에서 "기반:소스 N개" 이전 구간 추출
        # 현재 NotebookLM 구조: 스튜디오 → [버튼들] → [보고서 내용] → 기반:소스 N개
        studio_idx = body_text.find('\n스튜디오\n')
        if studio_idx >= 0:
            studio_section = body_text[studio_idx:]
            attrib_idx = studio_section.find('\n기반:소스')
            if attrib_idx > 50:
                content_area = studio_section[:attrib_idx]
                # 짧은 아이콘/버튼 라벨 제거 (20자 미만), 보고서 본문만 유지
                lines = [l.strip() for l in content_area.split('\n') if len(l.strip()) > 20]
                report = '\n'.join(lines)
                if len(report) > 100:
                    logger.info("[CUA] 스튜디오 구간 추출 성공: %d chars", len(report))
                    return report

        # 패턴 B: "기반:소스 N개" 직전 컨텐츠 블록
        sections = body_text.split('\n기반:소스')
        if len(sections) >= 2:
            content_area = sections[0]  # 첫 번째 "기반:소스" 이전
            lines = [l.strip() for l in content_area.split('\n') if len(l.strip()) > 20]
            report = '\n'.join(lines[-40:])  # 마지막 40개 실질 라인
            if len(report) > 100:
                logger.info("[CUA] 기반:소스 이전 구간 추출 성공: %d chars", len(report))
                return report

        # 패턴 C: 구버전 NotebookLM 구조 호환 ("소스 N개 기반")
        match = re.search(
            r'소스 \d+개 기반\n(.+?)(?=\nthumb_up|\nNotebookLM이)',
            body_text,
            re.DOTALL,
        )
        if match:
            report = match.group(1).strip()
            logger.info("[CUA] 구버전 regex 추출 성공: %d chars", len(report))
            return report

        logger.warning("[CUA] 모든 패턴 미발견 — body 전체 반환 (%d chars)", len(body_text))
        return body_text.strip()
    except Exception as e:
        logger.error("[CUA] body 텍스트 추출 실패: %s", e)
        return ""


def execute_action(page, action: dict) -> bool:
    """액션 실행. done이면 True 반환."""
    t = action.get("action")
    if t == "click":
        page.mouse.click(action["x"], action["y"])
        time.sleep(0.8)
    elif t == "type":
        page.keyboard.type(action["text"])
        time.sleep(0.3)
    elif t == "key":
        page.keyboard.press(action["key"])
        time.sleep(0.5)
    elif t == "scroll":
        page.mouse.move(action.get("x", 640), action.get("y", 400))
        page.mouse.wheel(0, action.get("delta_y", 300))
        time.sleep(0.3)
    elif t == "wait":
        time.sleep(action.get("ms", 2000) / 1000)
    elif t == "done":
        return True
    else:
        logger.warning("[CUA] 알 수 없는 액션: %s", t)
    return False


def generate_report(prompt: str, notebook_url: str, output_path: str, headless: bool = True) -> str:
    logger.info("[CUA] 시작 prompt=%r url=%s headless=%s", prompt, notebook_url, headless)
    client = OpenAI()
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    HISTORY_WINDOW = 3

    # Phase 1: 입력 필드 포커스까지만 — 프롬프트 텍스트 노출 없음
    TASK_PHASE1 = (
        "Task: Open the custom report input dialog in NotebookLM.\n"
        "Steps:\n"
        "1. If the Studio panel is not visible, click the Studio tab (right side)\n"
        "2. Click the '보고서' (report) tile\n"
        "3. Click '직접 만들기' (Custom) option\n"
        "4. Click inside the prompt text input field so it is focused\n"
        "Output {\"action\": \"done\"} when the text input field is focused and ready for input.\n"
        "Do NOT type anything yet — just navigate to and focus the input field."
    )

    # Phase 3a: Generate 버튼 클릭만 — 클릭 후 즉시 done
    TASK_PHASE3_CLICK = (
        "Task: Click the Generate (생성) button.\n"
        "The custom prompt text has already been typed in the input field.\n"
        "Find the blue Generate/생성 button and click it.\n"
        "Output {\"action\": \"done\"} immediately after clicking.\n"
        "Do NOT wait for the report to finish — just click Generate and output done."
    )

    # Phase 3b는 GPT 없이 Playwright 네이티브 대기로 처리
    PHASE3B_WAIT_MS = 180000  # 최대 3분

    def _run_cua_loop(page, task: str, max_steps: int, phase: str,
                      allowed_actions: set = None) -> bool:
        """CUA 루프 실행. done이면 True 반환.
        allowed_actions이 주어지면 그 외 액션은 wait으로 강제 대체."""
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
        for step in range(max_steps):
            screenshot_b64 = base64.b64encode(page.screenshot()).decode()
            logger.info("[CUA][%s] 스텝 %d/%d — gpt-5.4 Vision 호출", phase, step + 1, max_steps)

            history = msgs[1:]
            if len(history) > HISTORY_WINDOW * 2:
                history = history[-(HISTORY_WINDOW * 2):]
            msgs = [msgs[0]] + history

            msgs.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": task},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}",
                            "detail": "high",
                        },
                    },
                ],
            })

            response = client.chat.completions.create(
                model="gpt-5.4",
                messages=msgs,
                max_completion_tokens=256,
                temperature=0,
            )

            raw = (response.choices[0].message.content or "").strip()
            logger.info("[CUA][%s] 모델 응답: %s", phase, raw[:200])

            try:
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                action = json.loads(raw.strip())
            except json.JSONDecodeError as e:
                logger.error("[CUA][%s] JSON 파싱 실패: %s — %s", phase, e, raw)
                msgs.append({"role": "assistant", "content": raw})
                continue

            # 허용되지 않은 액션은 wait으로 강제 대체
            if allowed_actions and action.get("action") not in allowed_actions:
                logger.warning("[CUA][%s] 허용되지 않은 액션 차단 → wait: %s", phase, action)
                action = {"action": "wait", "ms": 3000}

            msgs.append({"role": "assistant", "content": raw})
            logger.info("[CUA][%s] 액션: %s", phase, action)

            if execute_action(page, action):
                return True

        return False

    with sync_playwright() as p:
        logger.info("[CUA] Chromium 시작")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()
        logger.info("[CUA] 노트북 URL 이동 중...")
        page.goto(notebook_url, wait_until="domcontentloaded", timeout=90000)
        time.sleep(3)
        logger.info("[CUA] 페이지 로드 완료: %s / url=%s", page.title(), page.url)

        _ensure_logged_in(page)
        time.sleep(2)

        # Phase 1: 입력 필드까지 내비게이션 (프롬프트 텍스트 GPT에 노출 안 함)
        logger.info("[CUA] Phase 1 시작: 보고서 입력 필드로 내비게이션")
        if not _run_cua_loop(page, TASK_PHASE1, max_steps=15, phase="P1"):
            context.close()
            raise RuntimeError("Phase 1 실패: 입력 필드 포커스 불가 (15 스텝 초과)")
        logger.info("[CUA] Phase 1 완료: 입력 필드 포커스됨")

        # Phase 2: Playwright로 직접 프롬프트 입력 (GPT에 프롬프트 텍스트 비노출)
        logger.info("[CUA] Phase 2: 프롬프트 직접 입력 (%d chars)", len(prompt))
        page.keyboard.type(prompt)
        time.sleep(1)
        logger.info("[CUA] Phase 2 완료: 프롬프트 입력됨")

        # Phase 3a: Generate 버튼 클릭
        logger.info("[CUA] Phase 3a 시작: Generate 버튼 클릭")
        if not _run_cua_loop(page, TASK_PHASE3_CLICK, max_steps=5, phase="P3a"):
            context.close()
            raise RuntimeError("Phase 3a 실패: Generate 버튼 클릭 불가 (5 스텝 초과)")
        logger.info("[CUA] Phase 3a 완료: Generate 버튼 클릭됨")
        time.sleep(3)  # 생성 시작 대기

        # Phase 3b: Playwright 네이티브 대기 (2단계)
        # Step 1: "보고서 생성 중" 나타날 때까지 기다림 (생성이 시작됐는지 확인)
        logger.info("[CUA] Phase 3b-1: '보고서 생성 중' 나타날 때까지 대기 (최대 30초)")
        try:
            page.wait_for_function(
                "() => document.body.innerText.includes('보고서 생성 중')",
                timeout=30000,
            )
            logger.info("[CUA] Phase 3b-1: '보고서 생성 중' 감지됨 — 생성 시작 확인")
        except Exception as e:
            logger.warning("[CUA] Phase 3b-1: '보고서 생성 중' 30초 내 미감지 (%s) — 이미 완료됐거나 다른 상태", e)

        # Step 2: "보고서 생성 중" 사라질 때까지 기다림 (생성 완료 확인)
        logger.info("[CUA] Phase 3b-2: '보고서 생성 중' 사라질 때까지 대기 (최대 %dms)", PHASE3B_WAIT_MS)
        try:
            page.wait_for_function(
                "() => !document.body.innerText.includes('보고서 생성 중')",
                timeout=PHASE3B_WAIT_MS,
            )
            logger.info("[CUA] Phase 3b-2 완료: '보고서 생성 중' 사라짐")
        except Exception as e:
            logger.warning("[CUA] Phase 3b-2 타임아웃 (%dms): %s — 강제 추출 시도", PHASE3B_WAIT_MS, e)

        time.sleep(3)  # 렌더링 완전 안정화

        # 보고서 텍스트 DOM 추출
        logger.info("[CUA] DOM에서 보고서 텍스트 추출 중...")
        report_text = _extract_report_from_dom(page)
        context.close()

        if not report_text:
            raise RuntimeError("보고서 DOM 추출 결과 없음")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(report_text, encoding="utf-8")
        logger.info("[CUA] 보고서 저장 완료: %s (%d chars)", output_path, len(report_text))
        return output_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--notebook-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    result = generate_report(args.prompt, args.notebook_url, args.output, args.headless)
    print(f"✅ {result}")


if __name__ == "__main__":
    main()
