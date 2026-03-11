"""
Configuration for NotebookLM Skill (Anti-Gravity Project Version)
인증(browser state)은 공유 스킬 데이터를 사용하고,
notebook 라이브러리는 프로젝트 전용으로 분리합니다.
"""

from pathlib import Path

# 프로젝트 로컬 디렉터리
SKILL_DIR = Path(__file__).parent.parent
DATA_DIR = SKILL_DIR / "data"

# 인증/브라우저 상태는 공유 스킬 데이터 사용 (재인증 불필요)
_SHARED_DATA_DIR = Path.home() / ".claude" / "skills" / "notebooklm" / "data"
BROWSER_STATE_DIR = _SHARED_DATA_DIR / "browser_state"
BROWSER_PROFILE_DIR = BROWSER_STATE_DIR / "browser_profile"
STATE_FILE = BROWSER_STATE_DIR / "state.json"
AUTH_INFO_FILE = _SHARED_DATA_DIR / "auth_info.json"

# notebook 라이브러리는 프로젝트 전용
LIBRARY_FILE = DATA_DIR / "library.json"

# NotebookLM Selectors
QUERY_INPUT_SELECTORS = [
    "textarea.query-box-input",  # Primary
    'textarea[aria-label="Feld für Anfragen"]',  # Fallback German
    'textarea[aria-label="Input for queries"]',  # Fallback English
]

RESPONSE_SELECTORS = [
    ".to-user-container .message-text-content",  # Primary
    "[data-message-author='bot']",
    "[data-message-author='assistant']",
]

# Browser Configuration
BROWSER_ARGS = [
    '--disable-blink-features=AutomationControlled',  # Patches navigator.webdriver
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--no-first-run',
    '--no-default-browser-check'
]

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Timeouts
LOGIN_TIMEOUT_MINUTES = 10
QUERY_TIMEOUT_SECONDS = 120
PAGE_LOAD_TIMEOUT = 30000
