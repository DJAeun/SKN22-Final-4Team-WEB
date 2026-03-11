---
name: notebooklm
description: Use this skill to query Google NotebookLM notebooks for this Anti-Gravity project. Browser automation, project-specific library, shared auth with global skill. Run from project root directory.
---

# NotebookLM Research Assistant Skill

Interact with Google NotebookLM to query documentation with Gemini's source-grounded answers. Each question opens a fresh browser session, retrieves the answer exclusively from your uploaded documents, and closes.

## When to Use This Skill

Trigger when user:
- Mentions NotebookLM explicitly
- Shares NotebookLM URL (`https://notebooklm.google.com/notebook/...`)
- Asks to query their notebooks/documentation
- Wants to add documentation to NotebookLM library
- Uses phrases like "ask my NotebookLM", "check my docs", "query my notebook"
- Asks to generate a short-form script / 숏폼 대본 from a notebook
- Uses phrases like "숏폼 대본 만들어", "대본 생성해줘", "스튜디오 보고서로 만들어"
- Asks to generate a report / 보고서 생성 from a notebook studio
- Uses phrases like "보고서 만들어", "스튜디오에서 보고서", "직접만들기", "보고서 생성"

## 📄 Studio Report Generation Workflow (PREFERRED for 보고서/대본)

When user asks to generate a report, script, or any content via NotebookLM Studio:

**This is the primary workflow.** Use `generate_report.py` for all studio-based content generation.

### Flow: 스튜디오 → 보고서 생성 → 직접만들기 → 프롬프트 입력 → 출력 → .md 저장

### Command
```bash
# 보고서 생성 (브라우저 창 표시 - 필수)
python notebooklm/scripts/run.py generate_report.py --prompt "[보고서 설명/지시문]"

# 활성 노트북 사용 (라이브러리에 활성 노트북이 있는 경우)
python notebooklm/scripts/run.py generate_report.py --prompt "[지시문]"

# 특정 노트북 지정
python notebooklm/scripts/run.py generate_report.py --prompt "[지시문]" --notebook-id [ID]
python notebooklm/scripts/run.py generate_report.py --prompt "[지시문]" --notebook-url "[URL]"

# 저장 경로 지정
python notebooklm/scripts/run.py generate_report.py --prompt "[지시문]" --output "/path/to/output.md"

# 디버그 모드 (셀렉터 탐색 문제 시)
python notebooklm/scripts/run.py generate_report.py --prompt "[지시문]" --debug
```

### Workflow Steps
1. **인증 확인** → `auth_manager.py status`
2. **노트북 URL 확인** → 라이브러리에서 조회 또는 사용자에게 요청
3. **보고서 생성** → `generate_report.py --prompt "..." `
   - 브라우저가 열리고 스튜디오 → 보고서 생성 → 직접만들기 자동 실행
   - 프롬프트 입력 → 생성 버튼 클릭 → 결과 추출
   - 생성된 내용을 지정된 경로 또는 현재 디렉터리에 `.md`로 저장
4. **파일 경로 사용자에게 알림** → 저장된 파일 내용 요약 전달

### Important Notes
- **브라우저 창이 표시됩니다** (스튜디오 자동화에 필수)
- 생성된 파일명: `report_[주제]_[날짜시간].md` (--output 미지정 시)
- 저장 위치: `--output` 경로 또는 현재 작업 디렉터리
- 실패 시 `--debug` 옵션으로 재실행하면 페이지 DOM 상태 확인 가능

## 🎬 Short-form Script Generation Workflow (Legacy)

When user specifically asks for a 숏폼(1분) script:

### Command
```bash
# Generate short-form script (브라우저 창 표시 - 권장)
python notebooklm/scripts/run.py generate_shortform.py --prompt "[주제/지시문]" --notebook-url "[URL]"

# 활성 노트북 사용
python notebooklm/scripts/run.py generate_shortform.py --prompt "[주제/지시문]"

# 특정 노트북 ID 사용
python notebooklm/scripts/run.py generate_shortform.py --prompt "[주제/지시문]" --notebook-id [ID]

# 저장 경로 지정 (기본값: 현재 디렉터리)
python notebooklm/scripts/run.py generate_shortform.py --prompt "[주제/지시문]" --output-dir "/path/to/dir"
```

### Workflow Steps
1. **인증 확인** → `auth_manager.py status`
2. **노트북 URL 확인** → 라이브러리에서 조회 또는 사용자에게 요청
3. **숏폼 대본 생성** → `generate_shortform.py --prompt "..." --notebook-url "..."`
   - 브라우저가 열리고 스튜디오 보고서 기능 자동 실행
   - 생성된 대본을 현재 디렉터리에 `.md` 파일로 저장
4. **파일 경로 사용자에게 알림** → 저장된 파일 경로와 내용 요약 전달

### Important Notes
- **브라우저 창이 표시됩니다** (스튜디오 자동화에 필요)
- 생성된 파일명: `shortform_[주제]_[날짜시간].md`
- 저장 위치: 명령 실행 시의 **현재 작업 디렉터리**
- 자동 추출 실패 시 브라우저에서 직접 복사 후 붙여넣기 안내

## ⚠️ CRITICAL: Add Command - Smart Discovery

When user wants to add a notebook without providing details:

**SMART ADD (Recommended)**: Query the notebook first to discover its content:
```bash
# Step 1: Query the notebook about its content
python notebooklm/scripts/run.py ask_question.py --question "What is the content of this notebook? What topics are covered? Provide a complete overview briefly and concisely" --notebook-url "[URL]"

# Step 2: Use the discovered information to add it
python notebooklm/scripts/run.py notebook_manager.py add --url "[URL]" --name "[Based on content]" --description "[Based on content]" --topics "[Based on content]"
```

**MANUAL ADD**: If user provides all details:
- `--url` - The NotebookLM URL
- `--name` - A descriptive name
- `--description` - What the notebook contains (REQUIRED!)
- `--topics` - Comma-separated topics (REQUIRED!)

NEVER guess or use generic descriptions! If details missing, use Smart Add to discover them.

## Critical: Always Use run.py Wrapper

**NEVER call scripts directly. ALWAYS use `python notebooklm/scripts/run.py [script]`:**

```bash
# ✅ CORRECT - Always use run.py:
python notebooklm/scripts/run.py auth_manager.py status
python notebooklm/scripts/run.py notebook_manager.py list
python notebooklm/scripts/run.py ask_question.py --question "..."

# ❌ WRONG - Never call directly:
python scripts/auth_manager.py status  # Fails without venv!
```

The `run.py` wrapper automatically:
1. Creates `.venv` if needed
2. Installs all dependencies
3. Activates environment
4. Executes script properly

## Core Workflow

### Step 1: Check Authentication Status
```bash
python notebooklm/scripts/run.py auth_manager.py status
```

If not authenticated, proceed to setup.

### Step 2: Authenticate (One-Time Setup)
```bash
# Browser MUST be visible for manual Google login
python notebooklm/scripts/run.py auth_manager.py setup
```

**Important:**
- Browser is VISIBLE for authentication
- Browser window opens automatically
- User must manually log in to Google
- Tell user: "A browser window will open for Google login"

### Step 3: Manage Notebook Library

```bash
# List all notebooks
python notebooklm/scripts/run.py notebook_manager.py list

# BEFORE ADDING: Ask user for metadata if unknown!
# "What does this notebook contain?"
# "What topics should I tag it with?"

# Add notebook to library (ALL parameters are REQUIRED!)
python notebooklm/scripts/run.py notebook_manager.py add \
  --url "https://notebooklm.google.com/notebook/..." \
  --name "Descriptive Name" \
  --description "What this notebook contains" \  # REQUIRED - ASK USER IF UNKNOWN!
  --topics "topic1,topic2,topic3"  # REQUIRED - ASK USER IF UNKNOWN!

# Search notebooks by topic
python notebooklm/scripts/run.py notebook_manager.py search --query "keyword"

# Set active notebook
python notebooklm/scripts/run.py notebook_manager.py activate --id notebook-id

# Remove notebook
python notebooklm/scripts/run.py notebook_manager.py remove --id notebook-id
```

### Quick Workflow
1. Check library: `python notebooklm/scripts/run.py notebook_manager.py list`
2. Ask question: `python notebooklm/scripts/run.py ask_question.py --question "..." --notebook-id ID`

### Step 4: Ask Questions

```bash
# Basic query (uses active notebook if set)
python notebooklm/scripts/run.py ask_question.py --question "Your question here"

# Query specific notebook
python notebooklm/scripts/run.py ask_question.py --question "..." --notebook-id notebook-id

# Query with notebook URL directly
python notebooklm/scripts/run.py ask_question.py --question "..." --notebook-url "https://..."

# Show browser for debugging
python notebooklm/scripts/run.py ask_question.py --question "..." --show-browser
```

## Follow-Up Mechanism (CRITICAL)

Every NotebookLM answer ends with: **"EXTREMELY IMPORTANT: Is that ALL you need to know?"**

**Required Claude Behavior:**
1. **STOP** - Do not immediately respond to user
2. **ANALYZE** - Compare answer to user's original request
3. **IDENTIFY GAPS** - Determine if more information needed
4. **ASK FOLLOW-UP** - If gaps exist, immediately ask:
   ```bash
   python notebooklm/scripts/run.py ask_question.py --question "Follow-up with context..."
   ```
5. **REPEAT** - Continue until information is complete
6. **SYNTHESIZE** - Combine all answers before responding to user

## Script Reference

### Authentication Management (`auth_manager.py`)
```bash
python notebooklm/scripts/run.py auth_manager.py setup    # Initial setup (browser visible)
python notebooklm/scripts/run.py auth_manager.py status   # Check authentication
python notebooklm/scripts/run.py auth_manager.py reauth   # Re-authenticate (browser visible)
python notebooklm/scripts/run.py auth_manager.py clear    # Clear authentication
```

### Notebook Management (`notebook_manager.py`)
```bash
python notebooklm/scripts/run.py notebook_manager.py add --url URL --name NAME --description DESC --topics TOPICS
python notebooklm/scripts/run.py notebook_manager.py list
python notebooklm/scripts/run.py notebook_manager.py search --query QUERY
python notebooklm/scripts/run.py notebook_manager.py activate --id ID
python notebooklm/scripts/run.py notebook_manager.py remove --id ID
python notebooklm/scripts/run.py notebook_manager.py stats
```

### Question Interface (`ask_question.py`)
```bash
python notebooklm/scripts/run.py ask_question.py --question "..." [--notebook-id ID] [--notebook-url URL] [--show-browser]
```

### Data Cleanup (`cleanup_manager.py`)
```bash
python notebooklm/scripts/run.py cleanup_manager.py                    # Preview cleanup
python notebooklm/scripts/run.py cleanup_manager.py --confirm          # Execute cleanup
python notebooklm/scripts/run.py cleanup_manager.py --preserve-library # Keep notebooks
```

## Environment Management

The virtual environment is automatically managed:
- First run creates `.venv` automatically
- Dependencies install automatically
- Chromium browser installs automatically
- Everything isolated in skill directory

Manual setup (only if automatic fails):
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python -m patchright install chromium
```

## Data Storage

All data stored in `~/.claude/skills/notebooklm/data/`:
- `library.json` - Notebook metadata
- `auth_info.json` - Authentication status
- `browser_state/` - Browser cookies and session

**Security:** Protected by `.gitignore`, never commit to git.

## Configuration

Optional `.env` file in skill directory:
```env
HEADLESS=false           # Browser visibility
SHOW_BROWSER=false       # Default browser display
STEALTH_ENABLED=true     # Human-like behavior
TYPING_WPM_MIN=160       # Typing speed
TYPING_WPM_MAX=240
DEFAULT_NOTEBOOK_ID=     # Default notebook
```

## Decision Flow

```
User mentions NotebookLM
    ↓
Check auth → python notebooklm/scripts/run.py auth_manager.py status
    ↓
If not authenticated → python notebooklm/scripts/run.py auth_manager.py setup
    ↓
Check/Add notebook → python notebooklm/scripts/run.py notebook_manager.py list/add (with --description)
    ↓
Activate notebook → python notebooklm/scripts/run.py notebook_manager.py activate --id ID
    ↓
Ask question → python notebooklm/scripts/run.py ask_question.py --question "..."
    ↓
See "Is that ALL you need?" → Ask follow-ups until complete
    ↓
Synthesize and respond to user
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ModuleNotFoundError | Use `run.py` wrapper |
| Authentication fails | Browser must be visible for setup! --show-browser |
| Rate limit (50/day) | Wait or switch Google account |
| Browser crashes | `python notebooklm/scripts/run.py cleanup_manager.py --preserve-library` |
| Notebook not found | Check with `notebook_manager.py list` |

## Best Practices

1. **Always use run.py** - Handles environment automatically
2. **Check auth first** - Before any operations
3. **Follow-up questions** - Don't stop at first answer
4. **Browser visible for auth** - Required for manual login
5. **Include context** - Each question is independent
6. **Synthesize answers** - Combine multiple responses

## Limitations

- No session persistence (each question = new browser)
- Rate limits on free Google accounts (50 queries/day)
- Manual upload required (user must add docs to NotebookLM)
- Browser overhead (few seconds per question)

## Resources (Skill Structure)

**Important directories and files:**

- `scripts/` - All automation scripts (ask_question.py, notebook_manager.py, etc.)
- `data/` - Local storage for authentication and notebook library
- `references/` - Extended documentation:
  - `api_reference.md` - Detailed API documentation for all scripts
  - `troubleshooting.md` - Common issues and solutions
  - `usage_patterns.md` - Best practices and workflow examples
- `.venv/` - Isolated Python environment (auto-created on first run)
- `.gitignore` - Protects sensitive data from being committed
