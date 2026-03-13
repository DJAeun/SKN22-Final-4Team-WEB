"""
로컬 Mac에서 1회 실행 — Google 로그인 세션을 browser_profile에 저장.
AWS 배포 전 반드시 실행 후 rsync로 전송할 것.

사용법:
    pip install playwright
    playwright install chromium
    python scripts/setup_auth.py
"""
from pathlib import Path
from playwright.sync_api import sync_playwright

BROWSER_PROFILE_DIR = Path(__file__).parent.parent / "data" / "browser_state" / "browser_profile"


def main():
    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"브라우저 프로파일 경로: {BROWSER_PROFILE_DIR}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_PROFILE_DIR),
            headless=False,
        )
        page = context.new_page()
        page.goto("https://accounts.google.com")
        print("브라우저에서 Google 로그인을 완료하세요.")
        print("로그인 완료 후 이 터미널에서 Enter를 누르세요...")
        input()
        context.close()

    print("✅ 인증 완료. browser_profile이 저장되었습니다.")
    print(f"다음 명령으로 AWS에 전송하세요:")
    print(f"  rsync -av {BROWSER_PROFILE_DIR.parent}/ ec2-user@<AWS_IP>:~/ai-influencer/notebooklm-service/data/browser_state/")


if __name__ == "__main__":
    main()
