# Hari Evaluation Suite

Three tools for testing the live Hari chatting service at `wss://chatting-hari.com/ws/chat/`.

## Files

```
eval/
├── golden_dataset.json   # 54-item benchmark across 7 categories
├── judge_eval.py         # LLM-as-Judge evaluation (Anthropic Claude)
├── load_test.py          # WebSocket concurrent load test
├── results/              # Auto-created; JSON output per run
└── README.md
```

## Setup

```bash
pip install websockets httpx anthropic

# Set credentials as env vars (or pass via flags)
export HARI_TEST_USER=your_test_username
export HARI_TEST_PASS=your_test_password
export ANTHROPIC_API_KEY=sk-ant-...
```

## 1. Golden Dataset (`golden_dataset.json`)

54 items across 7 categories:

| Category | Items | Purpose |
|---|---|---|
| `persona_maintenance` | 12 | Hari stays human, not AI |
| `safety_red_team` | 12 | Jailbreaks, prompt injection, harmful requests |
| `domain_knowledge` | 9 | Tech news accuracy |
| `honorific_tone` | 5 | 반말/존댓말 matching |
| `multi_turn` | 5 | Context memory across turns |
| `out_of_scope` | 5 | Graceful domain deflection |
| `refusal_calibration` | 6 | Must NOT over-refuse benign queries |

Each item has: `must_include_keywords`, `must_exclude_keywords`, `tone`, `notes`.

## 2. LLM-as-Judge (`judge_eval.py`)

Connects to the live WS server, sends each dataset item, scores with Claude Sonnet.

```bash
# Full run (all 54 items)
python eval/judge_eval.py

# Smoke test (first 10 items, fast check)
python eval/judge_eval.py --smoke 10

# Single category
python eval/judge_eval.py --category safety_red_team

# Save results
python eval/judge_eval.py --output eval/results/baseline.json
```

**Scoring:** 1–5 scale. Pass threshold = score ≥ 4 AND no rule failures.

**Cost estimate:** ~$0.10–0.20 per full run (54 items × Claude Sonnet input+output).

## 3. Load Test (`load_test.py`)

```bash
# Smoke (1 user)
python eval/load_test.py --users 1

# Load test (10 concurrent users)
python eval/load_test.py --users 10

# Stress ramp (1→50 users, +5 every 30s)
python eval/load_test.py --ramp --max-users 50 --step 5 --step-duration 30
```

**SLOs checked automatically:**
- TTFT p50 < 1.0s
- TTFT p95 < 2.5s
- End-to-end p95 < 8.0s
- Error rate < 0.5%

## Recommended workflow

```
Update Hari prompt/logic
    ↓
python eval/judge_eval.py --smoke 10     # quick sanity check (< $0.05)
    ↓ if pass
python eval/judge_eval.py                # full 54-item eval, compare delta vs baseline
    ↓ if score ≥ baseline
python eval/load_test.py --users 10      # check no speed regression
    ↓ if SLOs pass
Deploy to production
    ↓
python eval/load_test.py --ramp --max-users 30   # post-deploy stress
```
