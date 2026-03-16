import argparse
import base64
import json
import logging
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
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


def _extract_report_from_dom(page) -> str:
    """DOM에서 보고서 텍스트를 직접 추출. GPT OCR 대신 Playwright 사용."""
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
            logger.info("[CUA] DOM 추출 성공: %d chars", len(result))
            return result.strip()
    except Exception as e:
        logger.warning("[CUA] DOM 셀렉터 추출 실패: %s", e)

    # 폴백: body 전체 텍스트
    try:
        text = page.inner_text("body")
        logger.info("[CUA] DOM 폴백(body) 추출: %d chars", len(text))
        return text.strip()
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

    task = (
        f"Task: Generate a NotebookLM report.\n"
        f"Steps: Click Studio tab → Click 'Create report' button → "
        f"Select '직접 만들기'(Custom) → Type '{prompt}' in the prompt field → "
        f"Click Generate → Wait for completion.\n"
        f"When the report is fully generated and visible, output {{\"action\": \"done\"}}.\n"
        f"Do NOT include the report text — it will be extracted automatically."
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

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
        logger.info("[CUA] 페이지 로드 완료: %s", page.title())

        for step in range(30):
            screenshot_b64 = base64.b64encode(page.screenshot()).decode()
            logger.info("[CUA] 스텝 %d/30 — gpt-5.4 Vision 호출", step + 1)

            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": task if step == 0 else "Current state. What is the next action?"},
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
                messages=messages,
                max_completion_tokens=256,
                temperature=0,
            )

            raw = response.choices[0].message.content.strip()
            logger.info("[CUA] 모델 응답: %s", raw[:200])

            # JSON 파싱
            try:
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                action = json.loads(raw.strip())
            except json.JSONDecodeError as e:
                logger.error("[CUA] JSON 파싱 실패: %s — %s", e, raw)
                messages.append({"role": "assistant", "content": raw})
                continue

            messages.append({"role": "assistant", "content": raw})
            logger.info("[CUA] 액션: %s", action)

            done = execute_action(page, action)
            if done:
                logger.info("[CUA] done 감지 — DOM에서 보고서 텍스트 추출 중...")
                report_text = _extract_report_from_dom(page)
                if report_text:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(report_text, encoding="utf-8")
                    logger.info("[CUA] 보고서 저장 완료: %s (%d chars)", output_path, len(report_text))
                    context.close()
                    return output_path
                else:
                    logger.error("[CUA] DOM 추출 결과 없음")
                    break

        context.close()

    raise RuntimeError("보고서 생성 실패: 30 스텝 초과")


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
