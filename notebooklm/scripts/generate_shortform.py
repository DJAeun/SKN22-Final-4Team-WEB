#!/usr/bin/env python3
"""
NotebookLM Studio - Short-form Script Generator
스튜디오의 보고서 기능을 사용하여 1분짜리 숏폼 대본을 생성하고
현재 디렉터리에 .md 파일로 저장합니다.
"""

import argparse
import sys
import time
import re
import os
from pathlib import Path
from datetime import datetime

from patchright.sync_api import sync_playwright

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils


# Studio panel selectors
STUDIO_REPORT_SELECTORS = [
    "text=보고서",
    "button:has-text('보고서')",
    "[aria-label*='보고서']",
    "text=Report",
    "button:has-text('Report')",
]

STUDIO_PROMPT_SELECTORS = [
    "textarea[placeholder*='주제']",
    "textarea[placeholder*='topic']",
    "textarea[placeholder*='내용']",
    "textarea[placeholder*='Topic']",
    "textarea[placeholder*='Write about']",
    "input[placeholder*='주제']",
    "textarea.customize-input",
    "textarea[data-placeholder]",
]

STUDIO_GENERATE_SELECTORS = [
    "button:has-text('생성')",
    "button:has-text('만들기')",
    "button:has-text('Generate')",
    "button:has-text('Create')",
    "[aria-label*='생성']",
    "[aria-label*='Generate']",
]

STUDIO_CONTENT_SELECTORS = [
    ".studio-document-content",
    ".report-body",
    ".generated-report",
    "note-reader .note-body",
    ".studio-output-content",
    "div[data-note-id] .note-content",
    ".document-content",
    "article.studio-article",
]


def _find_and_click(page, selectors: list, label: str, timeout: int = 5000) -> bool:
    """여러 셀렉터를 순서대로 시도하여 요소를 찾고 클릭"""
    for selector in selectors:
        try:
            el = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if el:
                print(f"  ✓ Found {label}: {selector}")
                StealthUtils.random_delay(300, 600)
                el.click()
                return True
        except Exception:
            continue
    print(f"  ❌ Could not find {label}")
    return False


def _extract_studio_content(page, timeout: int = 120) -> str | None:
    """생성된 스튜디오 콘텐츠를 추출 (안정화될 때까지 대기)"""
    deadline = time.time() + timeout
    last_text = None
    stable_count = 0

    while time.time() < deadline:
        # 로딩 중인지 확인
        try:
            loading = page.query_selector(".loading-indicator, .spinner, [aria-busy='true']")
            if loading and loading.is_visible():
                time.sleep(1)
                continue
        except Exception:
            pass

        for selector in STUDIO_CONTENT_SELECTORS:
            try:
                elements = page.query_selector_all(selector)
                if elements:
                    text = elements[-1].inner_text().strip()
                    if text and len(text) > 100:
                        if text == last_text:
                            stable_count += 1
                            if stable_count >= 3:
                                return text
                        else:
                            stable_count = 0
                            last_text = text
                        break
            except Exception:
                continue

        time.sleep(1.5)

    return None


def generate_shortform(
    prompt: str,
    notebook_url: str,
    output_dir: str = None,
    headless: bool = False,
) -> str | None:
    """
    NotebookLM Studio 보고서 기능으로 1분짜리 숏폼 대본 생성 후 .md 저장

    Args:
        prompt: 숏폼 대본의 주제/내용 지시
        notebook_url: NotebookLM 노트북 URL
        output_dir: .md 파일 저장 경로 (기본값: 현재 디렉터리)
        headless: 브라우저 헤드리스 여부 (기본값: False - 창 표시)

    Returns:
        저장된 .md 파일 경로 또는 None
    """
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return None

    print(f"🎬 숏폼 대본 생성 시작: {prompt}")
    print(f"📚 Notebook: {notebook_url}")
    if not headless:
        print("  🖥️  브라우저 창이 열립니다 (스튜디오 자동화 진행 중)")

    playwright = None
    context = None

    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)

        page = context.new_page()
        print("  🌐 노트북 열기...")
        page.goto(notebook_url, wait_until="domcontentloaded")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)

        # 페이지 완전 로드 대기
        time.sleep(3)

        # 스튜디오 패널이 닫혀있으면 열기
        print("  🎨 스튜디오 패널 확인...")
        try:
            studio_toggle = page.wait_for_selector(
                "button[aria-label*='Studio'], button[aria-label*='스튜디오'], [data-panel='studio'] button",
                timeout=3000, state="visible"
            )
            if studio_toggle:
                studio_toggle.click()
                time.sleep(1)
        except Exception:
            pass  # 이미 열려있거나 다른 레이아웃

        # 보고서 버튼 찾기 & 클릭
        print("  📄 스튜디오 보고서 선택...")
        if not _find_and_click(page, STUDIO_REPORT_SELECTORS, "보고서 버튼"):
            print("\n  ℹ️  자동 탐색 실패. 브라우저에서 직접 '보고서'를 클릭한 후 Enter를 누르세요.")
            if not headless:
                input("  → 보고서 클릭 완료 후 Enter: ")
            else:
                return None

        StealthUtils.random_delay(1500, 2500)

        # 커스텀 프롬프트 입력창 찾기
        shortform_prompt = (
            f"다음 주제로 1분 분량(약 150~200자)의 숏폼 영상 대본을 작성해 주세요. "
            f"후킹 문장으로 시작하고, 핵심 내용을 간결하게 전달하며, "
            f"행동 유도 문구로 마무리하세요.\n\n주제: {prompt}"
        )

        print("  ✍️  프롬프트 입력...")
        prompt_found = False
        for selector in STUDIO_PROMPT_SELECTORS:
            try:
                el = page.wait_for_selector(selector, timeout=3000, state="visible")
                if el:
                    print(f"  ✓ 프롬프트 입력창 발견: {selector}")
                    el.click()
                    el.fill("")  # 기존 내용 지우기
                    StealthUtils.human_type(page, selector, shortform_prompt)
                    prompt_found = True
                    break
            except Exception:
                continue

        if not prompt_found:
            print("  ⚠️  프롬프트 입력창을 찾지 못했습니다. 기본 보고서로 진행합니다.")

        StealthUtils.random_delay(500, 1000)

        # 생성 버튼 클릭
        print("  🚀 생성 시작...")
        if not _find_and_click(page, STUDIO_GENERATE_SELECTORS, "생성 버튼", timeout=5000):
            if not headless:
                print("  ℹ️  생성 버튼을 직접 클릭한 후 Enter를 누르세요.")
                input("  → 생성 버튼 클릭 완료 후 Enter: ")
            else:
                return None

        # 콘텐츠 생성 대기 및 추출
        print("  ⏳ 콘텐츠 생성 대기 중 (최대 2분)...")
        content = _extract_studio_content(page, timeout=120)

        # 자동 추출 실패 시 사용자에게 복사 요청
        if not content and not headless:
            print("\n  ⚠️  자동 추출 실패. 브라우저에서 생성된 내용을 복사하여 붙여넣기 해주세요.")
            print("  → 생성된 전체 대본 텍스트를 복사 후 아래에 붙여넣고 Enter 두 번:")
            lines = []
            while True:
                line = input()
                if line == "":
                    if lines:
                        break
                else:
                    lines.append(line)
            content = "\n".join(lines)

        if not content:
            print("  ❌ 콘텐츠를 가져오지 못했습니다.")
            return None

        print("  ✅ 대본 생성 완료!")

        # .md 파일 저장
        if output_dir is None:
            output_dir = os.getcwd()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w가-힣\s-]', '', prompt)[:30].strip().replace(" ", "_")
        filename = f"shortform_{safe_name}_{timestamp}.md"
        filepath = Path(output_dir) / filename

        md_content = f"""# 숏폼 대본: {prompt}

> **생성일시**: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}
> **소스**: NotebookLM Studio 보고서
> **노트북**: {notebook_url}

---

{content}
"""

        filepath.write_text(md_content, encoding="utf-8")
        print(f"\n💾 저장 완료: {filepath}")
        return str(filepath)

    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        if context:
            try:
                context.close()
            except Exception:
                pass
        if playwright:
            try:
                playwright.stop()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Studio 보고서로 1분 숏폼 대본 생성 후 .md 저장"
    )
    parser.add_argument("--prompt", required=True, help="숏폼 대본 주제/지시")
    parser.add_argument("--notebook-url", help="NotebookLM 노트북 URL")
    parser.add_argument("--notebook-id", help="라이브러리 노트북 ID")
    parser.add_argument("--output-dir", help=".md 저장 경로 (기본값: 현재 디렉터리)")
    parser.add_argument(
        "--headless", action="store_true",
        help="헤드리스 모드 (기본값: 브라우저 창 표시)"
    )

    args = parser.parse_args()

    # 노트북 URL 결정
    notebook_url = args.notebook_url

    if not notebook_url and args.notebook_id:
        library = NotebookLibrary()
        notebook = library.get_notebook(args.notebook_id)
        if notebook:
            notebook_url = notebook["url"]
        else:
            print(f"❌ Notebook '{args.notebook_id}' not found in library")
            return 1

    if not notebook_url:
        library = NotebookLibrary()
        active = library.get_active_notebook()
        if active:
            notebook_url = active["url"]
            print(f"📚 활성 노트북 사용: {active['name']}")
        else:
            notebooks = library.list_notebooks()
            if notebooks:
                print("\n📚 사용 가능한 노트북:")
                for nb in notebooks:
                    print(f"  {nb['id']}: {nb['name']}")
                print("\n--notebook-id 또는 --notebook-url 로 지정하세요.")
            else:
                print("❌ 라이브러리가 비어 있습니다. 먼저 노트북을 추가하세요.")
            return 1

    result = generate_shortform(
        prompt=args.prompt,
        notebook_url=notebook_url,
        output_dir=args.output_dir,
        headless=args.headless,
    )

    if result:
        print(f"\n✅ 완료! 파일 저장 경로: {result}")
        return 0
    else:
        print("\n❌ 숏폼 대본 생성에 실패했습니다.")
        print("  → --show-browser 없이 headless로 실패 시 브라우저 창이 필요합니다.")
        print("  → 기본 실행은 브라우저 창을 표시합니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
