import argparse
import base64
import sys
import time
from pathlib import Path
from datetime import datetime

from playwright.sync_api import sync_playwright
from openai import OpenAI

DATA_DIR = Path(__file__).parent.parent / "data"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_state" / "browser_profile"


def execute_action(page, action: dict):
    t = action.get("type")
    if t == "click":
        page.mouse.click(action["x"], action["y"])
    elif t == "double_click":
        page.mouse.dblclick(action["x"], action["y"])
    elif t == "type":
        page.keyboard.type(action["text"])
    elif t == "key":
        page.keyboard.press(action["key"])
    elif t == "scroll":
        page.mouse.wheel(action.get("delta_x", 0), action.get("delta_y", 0))
    elif t == "wait":
        time.sleep(action.get("ms", 1000) / 1000)
    time.sleep(0.5)  # 안정화


def generate_report(prompt: str, notebook_url: str, output_path: str, headless: bool = True) -> str:
    client = OpenAI()
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
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
        page.goto(notebook_url, wait_until="networkidle", timeout=60000)

        task = (
            f"NotebookLM 스튜디오에서 보고서를 생성하라.\n"
            f"순서: Studio(스튜디오) 탭 클릭 → 보고서 생성 버튼 클릭 → "
            f"'직접 만들기' 선택 → 프롬프트 입력란에 '{prompt}' 입력 → "
            f"생성 버튼 클릭 → 생성 완료 대기 → 보고서 전체 텍스트 읽기.\n"
            f"완료되면 정확히 'REPORT_DONE: <보고서 전체 텍스트>' 형식으로 응답하라."
        )
        messages = [{"role": "user", "content": task}]

        for step in range(30):
            screenshot_b64 = base64.b64encode(page.screenshot()).decode()
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{screenshot_b64}",
                            "detail": "high",
                        },
                    }
                ],
            })

            response = client.responses.create(
                model="gpt-5.4",
                tools=[
                    {
                        "type": "computer_use_preview",
                        "display_width": 1280,
                        "display_height": 800,
                        "environment": "browser",
                    }
                ],
                messages=messages,
                max_output_tokens=8192,
            )

            assistant_msgs = []
            report_text = None

            for output in response.output:
                if output.type == "computer_call":
                    execute_action(page, output.action)
                    assistant_msgs.append(output)
                elif output.type == "text":
                    if "REPORT_DONE:" in output.text:
                        report_text = output.text.split("REPORT_DONE:", 1)[1].strip()
                    assistant_msgs.append(output)

            if report_text:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_text(report_text, encoding="utf-8")
                context.close()
                return output_path

            messages.append({"role": "assistant", "content": assistant_msgs})

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
