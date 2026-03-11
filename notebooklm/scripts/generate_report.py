#!/usr/bin/env python3
"""
NotebookLM Studio - 보고서 생성 (직접 만들기)
흐름: 스튜디오 → 보고서 생성 → 직접만들기 → 프롬프트 입력 → 생성 → .md 저장
"""

import argparse
import sys
import time
import re
import os
from pathlib import Path
from datetime import datetime

from patchright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))

from auth_manager import AuthManager
from notebook_manager import NotebookLibrary
from browser_utils import BrowserFactory, StealthUtils


# ── 셀렉터 모음 ────────────────────────────────────────────────────────────────

# 스튜디오 패널 열기 버튼
STUDIO_TAB_SELECTORS = [
    "text=스튜디오",
    "button:has-text('스튜디오')",
    "[aria-label*='스튜디오']",
    "text=Studio",
    "button:has-text('Studio')",
]

# 보고서 생성 다이얼로그를 여는 트리거 (스튜디오 패널 내 버튼)
REPORT_OPEN_SELECTORS = [
    # 새 항목 추가 버튼 (+ 아이콘)
    "button[aria-label*='추가']",
    "button[aria-label*='새']",
    "[aria-label*='새 항목']",
    # 보고서 관련 버튼
    "button:has-text('보고서')",
    "text=보고서",
    "[aria-label*='보고서']",
    # 영문 fallback
    "button:has-text('Report')",
    "text=Report",
    "[aria-label*='report']",
    # 스튜디오 추가 버튼
    "studio-add-button",
    ".studio-add",
    "[data-type='report']",
]

# "직접만들기" 옵션 버튼 (보고서 생성 패널 내)
# 실제 DOM: aria-label='직접 만들기' (버튼에 텍스트 없음, 아이콘 버튼)
CUSTOM_MAKE_SELECTORS = [
    "[aria-label='직접 만들기']",
    "[aria-label='직접만들기']",
    "button:has-text('직접 만들기')",
    "button:has-text('직접만들기')",
    "text=직접 만들기",
    "text=직접만들기",
    "button:has-text('Custom')",
    "[aria-label*='직접']",
]

# 프롬프트 입력 textarea (보고서 설명 입력란)
# "직접 만들기" 클릭 후 나타나는 입력 폼
PROMPT_TEXTAREA_SELECTORS = [
    "textarea[placeholder*='만들려는 보고서']",
    "textarea[placeholder*='보고서를 설명']",
    "textarea[placeholder*='설명하세요']",
    "textarea[placeholder*='Describe']",
    "textarea[placeholder*='describe']",
    # 다이얼로그 내 textarea
    "mat-dialog-container textarea",
    ".dialog-content textarea",
    ".report-dialog textarea",
    # 폼 내 textarea
    "form textarea",
    # ContentEditable div (rich text input)
    'div[contenteditable="true"]',
    'div[role="textbox"]',
    # 마지막 수단: 보이는 모든 textarea
    "textarea",
]

# 언어 선택 드롭다운 (한국어 기본값 유지 → 선택 필요 없을 수도 있음)
LANG_SELECTOR = "mat-select, select[name*='lang'], [aria-label*='언어']"

# 생성 버튼
GENERATE_BTN_SELECTORS = [
    "button:has-text('생성')",
    "button[type='submit']:has-text('생성')",
    "[aria-label*='생성']",
    "button:has-text('Generate')",
    "button:has-text('Create')",
    "mat-dialog-container button:has-text('생성')",
]

# 다이얼로그 닫힘 감지 (생성 완료 후 다이얼로그가 사라짐)
DIALOG_SELECTORS = [
    "mat-dialog-container",
    ".cdk-overlay-container .mat-dialog",
    "[role='dialog']",
    ".dialog-container",
]

# 생성된 보고서 콘텐츠 셀렉터 (스튜디오 패널에 나타남)
REPORT_CONTENT_SELECTORS = [
    "note-reader",
    ".note-body",
    ".note-content",
    ".studio-document-content",
    ".report-content",
    ".report-body",
    "div[class*='report']",
    "div[class*='note-content']",
    "div[class*='studio-output']",
    "article",
    ".document-body",
    ".generated-content",
    # 스튜디오 패널 내 마지막 항목
    ".studio-panel .content-item:last-child",
]


# ── 유틸 함수 ──────────────────────────────────────────────────────────────────

def _find_and_click(page, selectors: list, label: str, timeout: int = 5000) -> bool:
    """여러 셀렉터를 순서대로 시도하여 요소를 찾고 클릭"""
    for selector in selectors:
        try:
            el = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if el:
                print(f"  ✓ {label} 발견: {selector}")
                StealthUtils.random_delay(200, 500)
                el.click()
                return True
        except Exception:
            continue
    print(f"  ❌ {label}를 찾지 못했습니다")
    return False


def _find_element(page, selectors: list, label: str, timeout: int = 5000):
    """여러 셀렉터로 요소를 찾아 반환"""
    for selector in selectors:
        try:
            el = page.wait_for_selector(selector, timeout=timeout, state="visible")
            if el:
                print(f"  ✓ {label} 발견: {selector}")
                return el
        except Exception:
            continue
    print(f"  ❌ {label}를 찾지 못했습니다")
    return None


def _wait_dialog_close(page, timeout: int = 180) -> bool:
    """보고서 생성 다이얼로그가 닫힐 때까지 대기 (생성 완료 신호)"""
    print(f"  ⏳ 보고서 생성 중 대기 (최대 {timeout}초)...")
    deadline = time.time() + timeout

    # 먼저 다이얼로그가 열려 있는지 확인
    dialog_visible = False
    for selector in DIALOG_SELECTORS:
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                dialog_visible = True
                break
        except Exception:
            pass

    if not dialog_visible:
        # 다이얼로그가 이미 없으면 생성 중인 상태로 간주
        print("  ℹ️  다이얼로그가 이미 닫혔거나 없음 → 콘텐츠 추출 시도")
        return True

    while time.time() < deadline:
        all_closed = True
        for selector in DIALOG_SELECTORS:
            try:
                el = page.query_selector(selector)
                if el and el.is_visible():
                    all_closed = False
                    break
            except Exception:
                pass
        if all_closed:
            print("  ✓ 다이얼로그 닫힘 (생성 완료)")
            return True
        time.sleep(1.5)

    print("  ⚠️  타임아웃: 다이얼로그가 닫히지 않음")
    return False


def _get_artifact_titles(page) -> list:
    """현재 스튜디오의 artifact 제목 목록 스냅샷 (순서 유지)"""
    try:
        titles = page.evaluate("""() => {
            const items = document.querySelectorAll('.artifact-button-content');
            return Array.from(items).map(el => (el.innerText || '').trim().slice(0, 80));
        }""")
        return titles if titles else []
    except Exception:
        return []


def _wait_new_artifact(page, known_titles: list, timeout: int = 300) -> str | None:
    """
    새 artifact 항목이 나타나고 생성이 완전히 완료될 때까지 대기.
    '생성 중' 상태가 사라지고 실제 제목이 나타나면 반환.
    """
    known_set = set(known_titles)
    print(f"  ⏳ 새 보고서 항목 대기 (최대 {timeout}초)...")
    deadline = time.time() + timeout
    found_generating = False

    while time.time() < deadline:
        try:
            current = page.evaluate("""() => {
                const items = document.querySelectorAll('.artifact-button-content');
                return Array.from(items).map(el => (el.innerText || '').trim().slice(0, 120));
            }""")
            if current:
                for title in current:
                    if not title or title in known_set:
                        continue
                    # 생성 중 상태 감지 (아이콘 텍스트 'sync' 또는 '생성 중' 포함)
                    is_generating = "생성 중" in title or title.strip().startswith("sync")
                    if is_generating:
                        if not found_generating:
                            print(f"  ⏳ 생성 중... 완료 대기")
                            found_generating = True
                    else:
                        # 생성 완료: 실제 제목 있는 항목
                        print(f"  ✓ 생성 완료: {title[:60]}")
                        return title
        except Exception:
            pass
        time.sleep(3)

    # 타임아웃: 그래도 항목이 있으면 첫 번째 사용
    print("  ⚠️  타임아웃 → 첫 번째 항목으로 진행")
    return None


def _open_report_viewer(page, new_title: str | None) -> bool:
    """
    스튜디오 목록의 artifact 항목 클릭해 report-viewer 열기.
    new_title이 있으면 해당 항목 우선, 없으면 첫 번째(최신) 항목 클릭.
    """
    try:
        # 모든 artifact 항목 조회
        els = page.query_selector_all(".artifact-button-content")
        if not els:
            print("  ❌ .artifact-button-content 없음")
            return False

        target = els[0]  # 기본: 첫 번째 (최신)

        if new_title:
            for el in els:
                try:
                    txt = el.inner_text().strip()
                    if new_title[:40] in txt:
                        target = el
                        break
                except Exception:
                    pass

        txt = target.inner_text().strip()[:60].replace('\n', '|')
        print(f"  ℹ️  클릭 대상: {txt!r}")
        box = target.bounding_box()
        if box:
            x = box['x'] + box['width'] * 0.35
            y = box['y'] + box['height'] / 2
            page.mouse.click(x, y)
            print("  ✓ artifact 클릭 (뷰어 로딩 대기 중...)")
            time.sleep(12)  # 뷰어 완전 로딩 대기
            return True
    except Exception as e:
        print(f"  ⚠️  클릭 실패: {e}")
    return False


def _extract_from_viewer(page, timeout: int = 60) -> str | None:
    """
    artifact-viewer의 content 영역에서 보고서 전체 텍스트 추출.
    확인된 셀렉터: .artifact-content, .artifact-content-scrollable
    """
    print(f"  ℹ️  뷰어 콘텐츠 추출 시도 (최대 {timeout}초)...")

    all_selectors = [
        # 확인된 최우선 셀렉터
        "report-viewer",
        "labs-tailwind-doc-viewer",
        "element-list-renderer",
        # 차선 셀렉터
        ".artifact-content",
        ".artifact-content-scrollable",
        "[class*='artifact-content']",
        ".artifact-viewer-container",
        "note-reader", ".note-body", "article",
        ".studio-document-content", ".report-content",
        ".document-body",
    ]

    deadline = time.time() + timeout
    last_js_text = None

    while time.time() < deadline:
        # JS 추출 시도 (가장 신뢰도 높음) - Playwright와 last_text 공유하지 않음
        try:
            result = page.evaluate("""() => {
                const sels = [
                    'report-viewer',
                    'labs-tailwind-doc-viewer',
                    'element-list-renderer',
                    '.artifact-content', '.artifact-content-scrollable',
                    '[class*="artifact-content"]',
                    '.artifact-viewer-container',
                    'note-reader', 'article'
                ];
                let best = '';
                for (const sel of sels) {
                    const els = document.querySelectorAll(sel);
                    for (const el of els) {
                        const t = (el.innerText || '').trim();
                        if (t.length > best.length && t.includes('\\n') && t.length > 200) {
                            best = t;
                        }
                    }
                }
                return best.length > 200 ? best : null;
            }""")
            if result:
                if result == last_js_text:
                    # 동일한 텍스트 두 번 연속 → 로딩 완료
                    print(f"  ✓ JS 추출 성공 ({len(result)}자)")
                    return result
                last_js_text = result
                print(f"  ℹ️  콘텐츠 로딩 중... ({len(result)}자 감지)")
                time.sleep(2)
                continue  # JS 경로에서 계속 확인
        except Exception:
            pass

        # JS 실패 시 Playwright 셀렉터 시도
        for sel in all_selectors:
            try:
                els = page.query_selector_all(sel)
                if els:
                    text = els[-1].inner_text().strip()
                    if len(text) > 200 and "\n" in text:
                        print(f"  ✓ 셀렉터 추출 성공: {sel} ({len(text)}자)")
                        return text
            except Exception:
                continue

        time.sleep(2)

    return None


def _extract_report_content(page, known_titles: list, timeout: int = 180) -> str | None:
    """생성된 보고서 전체 콘텐츠 추출 (새 항목 감지 → 클릭 → 뷰어 열기 → 텍스트 추출)"""

    # 1단계: 새 artifact 항목 등장 대기
    new_title = _wait_new_artifact(page, known_titles, timeout=timeout)
    time.sleep(2)

    # 2단계: 항목 클릭해서 뷰어 열기
    opened = _open_report_viewer(page, new_title)
    if not opened:
        print("  ⚠️  뷰어를 열지 못함, 직접 추출 시도")

    # 3단계: 뷰어에서 텍스트 추출 (충분한 시간 확보)
    content = _extract_from_viewer(page, timeout=90)
    return content


def _clean_content(text: str) -> str:
    """추출된 콘텐츠에서 NotebookLM UI 잔여 텍스트 제거"""
    # 앞부분 UI 요소 제거
    ui_prefixes = ["content_copy\n", "Based on 1 source\n", "Based on ", "arrow_back\n"]
    for prefix in ui_prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]
        idx = text.find("\n" + prefix)
        if idx != -1:
            # prefix 이전 내용이 없거나 짧으면 prefix 이후부터 사용
            before = text[:idx].strip()
            if len(before) < 50:
                text = text[idx + len(prefix) + 1:]

    # 뒷부분 UI 요소 제거 (thumb_up/down, 아티팩트 메시지 등)
    ui_suffixes = [
        "\nthumb_up\n",
        "\nthumb_down\n",
        "\n유용한 보고서\n",
        "\n유용하지 않은 보고서\n",
    ]
    for suffix in ui_suffixes:
        idx = text.find(suffix)
        if idx != -1:
            text = text[:idx]

    # "보고서 ... 아티팩트가 준비되었습니다" 제거
    import re as _re
    text = _re.sub(r'\n보고서 "[^"]*" 아티팩트가 준비되었습니다\.?\s*$', '', text)

    return text.strip()


def _dump_page_debug(page):
    """디버그용: 현재 페이지 버튼과 텍스트 출력"""
    print("\n  === DEBUG: 현재 버튼 목록 ===")
    for b in page.query_selector_all("button")[:30]:
        try:
            txt = b.inner_text().strip().replace("\n", " ")
            if txt:
                print(f"    BTN: {txt[:80]!r}")
        except Exception:
            pass
    print("  === DEBUG: aria-label 목록 ===")
    for el in page.query_selector_all("[aria-label]")[:20]:
        try:
            label = el.get_attribute("aria-label")
            if label:
                print(f"    aria-label={label!r}")
        except Exception:
            pass
    print("  ===========================\n")


# ── 메인 생성 함수 ─────────────────────────────────────────────────────────────

def generate_report(
    prompt: str,
    notebook_url: str,
    output_path: str = None,
    headless: bool = False,
    debug: bool = False,
) -> str | None:
    """
    NotebookLM Studio 보고서(직접 만들기) 생성 후 .md 저장

    흐름: 스튜디오 → 보고서 생성 → 직접만들기 → 프롬프트 → 생성 → 추출 → 저장

    Args:
        prompt: 보고서 설명 프롬프트 (사용자 자유 입력)
        notebook_url: NotebookLM 노트북 URL
        output_path: 저장할 .md 파일 경로 (기본값: 현재 디렉터리/report_*.md)
        headless: 헤드리스 모드 (기본값: False - 브라우저 창 표시)
        debug: 디버그 출력 활성화

    Returns:
        저장된 .md 파일 경로 또는 None
    """
    auth = AuthManager()
    if not auth.is_authenticated():
        print("⚠️  Not authenticated. Run: python scripts/run.py auth_manager.py setup")
        return None

    print(f"📝 보고서 생성 시작")
    print(f"   프롬프트: {prompt}")
    print(f"📚 Notebook: {notebook_url}")
    if not headless:
        print("  🖥️  브라우저 창이 열립니다")

    playwright = None
    context = None

    try:
        playwright = sync_playwright().start()
        context = BrowserFactory.launch_persistent_context(playwright, headless=headless)
        page = context.new_page()

        # ── 1. 노트북 열기 ────────────────────────────────────────────────────
        print("\n[1/6] 노트북 열기...")
        page.goto(notebook_url, wait_until="domcontentloaded")
        page.wait_for_url(re.compile(r"^https://notebooklm\.google\.com/"), timeout=15000)
        time.sleep(2)

        if debug:
            _dump_page_debug(page)

        # ── 2. 스튜디오 탭 클릭 (필요한 경우) ───────────────────────────────
        print("[2/6] 스튜디오 패널 확인...")
        for sel in STUDIO_TAB_SELECTORS:
            try:
                tab = page.wait_for_selector(sel, timeout=3000, state="visible")
                if tab:
                    tab.click()
                    print(f"  ✓ 스튜디오 탭 클릭: {sel}")
                    time.sleep(1)
                    break
            except Exception:
                continue

        # ── 2.5. 기존 artifact 목록 스냅샷 (생성 전 기준선) ──────────────────
        known_titles = _get_artifact_titles(page)
        print(f"  ℹ️  기존 artifact {len(known_titles)}개 스냅샷")

        # ── 3. "보고서 생성" 다이얼로그 열기 ─────────────────────────────────
        print("[3/6] 보고서 생성 다이얼로그 열기...")

        dialog_opened = False

        # 3a. 다이얼로그가 이미 열려있는지 확인
        for sel in DIALOG_SELECTORS:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    print("  ✓ 다이얼로그 이미 열려있음")
                    dialog_opened = True
                    break
            except Exception:
                pass

        # 3b. 보고서 버튼 클릭해서 열기
        if not dialog_opened:
            if _find_and_click(page, REPORT_OPEN_SELECTORS, "보고서 생성 버튼", timeout=5000):
                time.sleep(1)
                dialog_opened = True

        # 3c. 실패 시 디버그 출력
        if not dialog_opened:
            print("  ⚠️  보고서 생성 버튼을 찾지 못했습니다. 페이지 상태 확인...")
            if debug:
                _dump_page_debug(page)
            else:
                _dump_page_debug(page)  # 실패 시는 항상 출력
            print("  → 계속 진행 (textarea 직접 탐색)")

        # ── 4. "직접만들기" 클릭 ────────────────────────────────────────────
        print("[4/6] '직접 만들기' 클릭...")
        custom_clicked = False
        for sel in CUSTOM_MAKE_SELECTORS:
            try:
                el = page.wait_for_selector(sel, timeout=5000, state="visible")
                if el:
                    print(f"  ✓ '직접 만들기' 발견: {sel}")
                    el.click()
                    custom_clicked = True
                    time.sleep(1)  # 폼 렌더링 대기
                    break
            except Exception:
                continue
        if not custom_clicked:
            print("  ℹ️  '직접 만들기' 버튼 없음 (직접 입력 폼 사용)")

        # ── 5. 프롬프트 입력 ─────────────────────────────────────────────────
        print(f"[5/6] 프롬프트 입력: {prompt[:50]}...")
        textarea = _find_element(page, PROMPT_TEXTAREA_SELECTORS, "프롬프트 textarea", timeout=8000)

        if not textarea:
            print("  ❌ 프롬프트 입력창을 찾지 못했습니다.")
            if debug:
                _dump_page_debug(page)
            return None

        # 기존 내용 지우고 입력 (textarea / contenteditable 모두 지원)
        textarea.click()
        time.sleep(0.3)
        # Ctrl+A 후 Delete로 기존 내용 제거 (contenteditable 호환)
        textarea.press("Control+a")
        time.sleep(0.1)
        textarea.press("Delete")
        time.sleep(0.2)
        # fill() 시도 (일반 textarea)
        try:
            textarea.fill(prompt)
        except Exception:
            # contenteditable div 등 fill()이 안 되는 경우 type() 사용
            textarea.type(prompt, delay=30)
        time.sleep(0.5)
        print("  ✓ 프롬프트 입력 완료")

        # ── 6. 생성 버튼 클릭 ────────────────────────────────────────────────
        print("[6/6] '생성' 버튼 클릭...")
        if not _find_and_click(page, GENERATE_BTN_SELECTORS, "생성 버튼", timeout=5000):
            print("  ❌ 생성 버튼을 찾지 못했습니다.")
            _dump_page_debug(page)
            return None

        # ── 7. 생성 완료 대기 ────────────────────────────────────────────────
        print("\n  ⏳ 보고서 생성 중... (최대 3분)")
        _wait_dialog_close(page, timeout=180)
        time.sleep(5)  # 생성 후 렌더링 안정화

        # ── 8. 콘텐츠 추출 ───────────────────────────────────────────────────
        print("  🔍 생성된 콘텐츠 추출...")

        content = _extract_report_content(page, known_titles=known_titles, timeout=180)

        if not content:
            # 폴백: 클릭 후 body 텍스트에서 뷰어 영역 파싱
            print("  ⚠️  일반 추출 실패, body 텍스트 파싱 시도...")
            body_text = page.inner_text("body")

            # 뷰어가 열리면 body에 "arrow_back" 또는 "Based on" 마커가 나타남
            markers = ["arrow_back\n", "Based on 1 source\n", "content_copy\n"]
            cut_idx = -1
            for marker in markers:
                idx = body_text.find(marker)
                if idx != -1:
                    # 마커 이후 줄에서 실제 제목/내용이 시작됨
                    after = body_text[idx + len(marker):]
                    # 짧은 헤더 버튼 줄 건너뛰기 (arrow_back, more_horiz, content_copy)
                    lines = after.splitlines()
                    for i, line in enumerate(lines):
                        if len(line.strip()) > 10:
                            cut_idx = body_text.find(line)
                            break
                    break

            if cut_idx != -1:
                content = body_text[cut_idx:cut_idx + 10000].strip()
                print(f"  ✓ 뷰어 영역 파싱 성공 ({len(content)}자)")
            else:
                # 최후 수단: artifact-content 직접 JS 추출
                try:
                    content = page.evaluate("""() => {
                        const el = document.querySelector('.artifact-content, .artifact-content-scrollable, [class*="artifact-content"]');
                        return el ? el.innerText.trim() : null;
                    }""")
                    if content:
                        print(f"  ✓ JS artifact-content 추출 ({len(content)}자)")
                except Exception:
                    pass

        if not content:
            print("\n  ❌ 콘텐츠를 추출하지 못했습니다.")
            return None

        # UI 잔여 텍스트 제거
        content = _clean_content(content)
        print(f"  ✅ 콘텐츠 추출 완료 ({len(content)}자)")

        # ── 9. .md 파일 저장 ─────────────────────────────────────────────────
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w가-힣\s-]', '', prompt)[:30].strip().replace(" ", "_")
            filename = f"report_{safe_name}_{timestamp}.md"
            output_path = os.path.join(os.getcwd(), filename)

        md_content = f"""# 보고서: {prompt}

> **생성일시**: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}
> **소스**: NotebookLM Studio 보고서 (직접 만들기)
> **노트북**: {notebook_url}

---

{content}
"""

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(md_content, encoding="utf-8")
        print(f"\n💾 저장 완료: {output_path}")
        return output_path

    except Exception as e:
        print(f"\n  ❌ 오류 발생: {e}")
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


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="NotebookLM Studio 보고서 생성 (직접만들기) → .md 저장"
    )
    parser.add_argument(
        "--prompt", required=True,
        help="보고서 설명 프롬프트 (예: '하리의 세계관을 바탕으로 자기소개 대본 써주세요')"
    )
    parser.add_argument("--notebook-url", help="NotebookLM 노트북 URL")
    parser.add_argument("--notebook-id", help="라이브러리 노트북 ID")
    parser.add_argument("--output", help="저장할 .md 파일 경로 (기본값: 현재 디렉터리)")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--debug", action="store_true", help="디버그 출력 활성화")

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

    result = generate_report(
        prompt=args.prompt,
        notebook_url=notebook_url,
        output_path=args.output,
        headless=args.headless,
        debug=args.debug,
    )

    if result:
        print(f"\n✅ 완료! 저장 경로: {result}")
        return 0
    else:
        print("\n❌ 보고서 생성에 실패했습니다.")
        print("   팁: --debug 옵션으로 재실행하면 페이지 상태를 확인할 수 있습니다.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
