"""NotebookLM 노트북 생성 CUA 스크립트.

Usage:
  python3 create_notebook_cua.py \
    --name "AI뉴스 2025-03-18" \
    --topic "AI뉴스" \
    --channel-ids "UCxxxxxx,UCyyyyyy" \
    --output result.json \
    --headless

Output JSON:
  {"notebook_id": "nb_AI뉴스_20250318", "notebook_url": "https://notebooklm.google.com/..."}
"""

import argparse
import json
import logging
import sys
import time
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from generate_report_cua import (
    BROWSER_PROFILE_DIR,
    DATA_DIR,
    _ensure_logged_in,
    _run_cua_loop,
)
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("create_notebook_cua")

NOTEBOOKLM_HOME = "https://notebooklm.google.com"
LIBRARY_JSON = DATA_DIR / "library.json"


# ─────────────────────────────────────────
# library.json 토픽 관리
# ─────────────────────────────────────────

def _load_library() -> dict:
    if LIBRARY_JSON.exists():
        try:
            return json.loads(LIBRARY_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"notebooks": {}, "topics": {}}


def _save_library(lib: dict) -> None:
    LIBRARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    LIBRARY_JSON.write_text(
        json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _register_notebook(
    notebook_id: str,
    notebook_url: str,
    notebook_name: str,
    topic: str,
    channel_ids: list[str],
) -> None:
    """library.json에 새 노트북 등록 및 토픽 active 업데이트."""
    lib = _load_library()
    today = date.today().isoformat()

    # notebooks 섹션 등록
    lib.setdefault("notebooks", {})[notebook_id] = {
        "name": notebook_name,
        "url": notebook_url,
        "topic": topic,
        "date": today,
    }

    # topics 섹션 업데이트
    topics = lib.setdefault("topics", {})
    if topic not in topics:
        topics[topic] = {"channel_ids": channel_ids, "history": []}

    topics[topic]["active_notebook_id"] = notebook_id
    topics[topic]["channel_ids"] = channel_ids or topics[topic].get("channel_ids", [])
    topics[topic].setdefault("history", []).insert(0, {
        "notebook_id": notebook_id,
        "date": today,
        "url": notebook_url,
    })
    # history는 최근 30일만 유지
    topics[topic]["history"] = topics[topic]["history"][:30]

    # 기본 active_notebook_id 유지 (기존 동작 하위 호환)
    if not lib.get("active_notebook_id"):
        lib["active_notebook_id"] = notebook_id

    _save_library(lib)
    logger.info("[library] 등록 완료: %s → %s", topic, notebook_id)


# ─────────────────────────────────────────
# CUA 노트북 생성
# ─────────────────────────────────────────

def create_notebook(page, client, notebook_name: str) -> str:
    """CUA로 NotebookLM 홈에서 새 노트북을 생성하고 URL을 반환."""
    logger.info("[create_notebook] 홈 이동: %s", NOTEBOOKLM_HOME)
    page.goto(NOTEBOOKLM_HOME, wait_until="domcontentloaded", timeout=90000)
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:
        pass
    _ensure_logged_in(page)
    time.sleep(2)

    TASK = (
        "Task: Create a new notebook on NotebookLM.\n"
        f"Notebook name to set: '{notebook_name}'\n"
        "Steps:\n"
        "1. On the NotebookLM home page, find the '새 노트북' or '+ New notebook' or 'Create' button\n"
        "2. Click it\n"
        "3. If a name/title input dialog appears, clear any existing text and type the notebook name\n"
        f"   Name: {notebook_name}\n"
        "4. Confirm by pressing Enter or clicking the create/확인/OK button\n"
        "5. Wait for the new empty notebook page to fully load\n"
        f'Output {{"action": "done"}} when the new notebook page is open and the URL has changed to the notebook URL.\n'
        "Do NOT add any sources yet — just create the empty notebook."
    )

    if not _run_cua_loop(page, client, TASK, max_steps=12, phase="CREATE_NB"):
        raise RuntimeError("노트북 생성 실패 (12 스텝 초과)")

    time.sleep(2)
    notebook_url = page.url
    logger.info("[create_notebook] 생성 완료: %s", notebook_url)

    if "notebooklm.google.com/notebook/" not in notebook_url:
        raise RuntimeError(f"노트북 URL 획득 실패: {notebook_url}")

    return notebook_url


# ─────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help="노트북 표시 이름 (예: 'AI뉴스 2025-03-18')")
    parser.add_argument("--topic", default="", help="토픽 키 (예: 'AI뉴스')")
    parser.add_argument("--channel-ids", default="", help="콤마 구분 YouTube 채널 ID 목록")
    parser.add_argument("--output", default="", help="결과 JSON 출력 경로")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI()

    channel_ids = [c.strip() for c in args.channel_ids.split(",") if c.strip()]
    today = date.today().strftime("%Y%m%d")
    topic_slug = args.topic.replace(" ", "_") if args.topic else "default"
    notebook_id = f"nb_{topic_slug}_{today}"

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=args.headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        notebook_url = create_notebook(page, client, args.name)
        context.close()

    _register_notebook(
        notebook_id=notebook_id,
        notebook_url=notebook_url,
        notebook_name=args.name,
        topic=args.topic,
        channel_ids=channel_ids,
    )

    result = {"notebook_id": notebook_id, "notebook_url": notebook_url}

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False))
    print(f"✅ Created: {notebook_id} → {notebook_url}")


if __name__ == "__main__":
    main()
