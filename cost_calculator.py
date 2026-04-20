"""
Cost Calculator for Chatting Service
=====================================
Estimates per-turn, per-session, and monthly costs for:
  1. Hari Chat Service (OpenAI models)
  2. RPG Roleplay Service (Google Gemini)

Pricing as of April 2026.
"""

# ─── Model Pricing (USD per 1M tokens) ───────────────────────────────────────

PRICING = {
    # OpenAI models
    "gpt-5.3-chat-latest":     {"input": 1.75,  "output": 14.00},
    "gpt-5.4-mini":            {"input": 0.25,  "output": 2.00},
    "gpt-4o-mini":             {"input": 0.15,  "output": 0.60},
    "text-embedding-3-small":  {"input": 0.02,  "output": 0.00},
    # Google Gemini (≤200K context)
    "gemini-3.1-pro-preview":  {"input": 2.00,  "output": 12.00},
}


def cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a single LLM call."""
    p = PRICING[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000


# ─── Hari Chat Service: Per-Turn Token Estimates ─────────────────────────────
# A single user message triggers up to 6 LLM/embedding calls.

HARI_CALLS = {
    "1. Main response (gpt-5.3-chat-latest)": {
        "model": "gpt-5.3-chat-latest",
        "input_tokens": 4000,   # system prompt (~1500) + memory context (~1500) + user msg + history
        "output_tokens": 400,   # short Korean reply (3 sentences)
        "probability": 1.0,
        "note": "Always called. System prompt + persona + memory + knowledge + user input",
    },
    "2. Knowledge boundary (gpt-5.4-mini)": {
        "model": "gpt-5.4-mini",
        "input_tokens": 500,    # classifier system prompt + user message
        "output_tokens": 50,    # structured output (JSON)
        "probability": 1.0,
        "note": "Always called. Classifies knowledge level + search decision",
    },
    "3. Preference intent (gpt-4o-mini)": {
        "model": "gpt-4o-mini",
        "input_tokens": 600,    # classifier prompt + user message
        "output_tokens": 50,    # structured output
        "probability": 0.15,    # regex prefilter skips ~85% of messages
        "note": "Only when regex detects preference-like phrases",
    },
    "4. Web search summary (gpt-5.4-mini)": {
        "model": "gpt-5.4-mini",
        "input_tokens": 300,    # search decision prompt + user message
        "output_tokens": 50,    # structured output
        "probability": 0.20,    # only for tech-related questions
        "note": "Only when knowledge boundary says KNOWS + needs search",
    },
    "5. Embeddings - retrieval (text-embedding-3-small)": {
        "model": "text-embedding-3-small",
        "input_tokens": 200,    # user query embedding for vector search
        "output_tokens": 0,
        "probability": 1.0,
        "note": "3 embed calls: hari_knowledge + user_persona + chat_memory retrieval",
    },
    "6. Session end: summarize (gpt-5.4-mini)": {
        "model": "gpt-5.4-mini",
        "input_tokens": 2000,   # full conversation transcript
        "output_tokens": 200,   # 2-4 sentence summary
        "probability": 0.05,    # once per session (amortized: ~1/20 turns)
        "note": "Called once at disconnect. Amortized across ~20 turns/session",
    },
    "7. Session end: memory extraction (gpt-5.4-mini)": {
        "model": "gpt-5.4-mini",
        "input_tokens": 2000,   # conversation transcript
        "output_tokens": 300,   # extracted facts
        "probability": 0.05,    # once per session
        "note": "Extracts user facts at session end. Amortized across ~20 turns",
    },
    "8. Session end: summary embedding (text-embedding-3-small)": {
        "model": "text-embedding-3-small",
        "input_tokens": 100,    # summary text
        "output_tokens": 0,
        "probability": 0.05,    # once per session
        "note": "Embeds the conversation summary for future retrieval",
    },
}


# ─── RPG Roleplay Service: Per-Turn Token Estimates ─────────────────────────

RPG_CALLS = {
    "1. Main response (gemini-3.1-pro-preview)": {
        "model": "gemini-3.1-pro-preview",
        "input_tokens": 8000,   # llm_rule.md (~4500 tokens for 18KB Korean) + lorebooks + 15 recent logs + memory
        "output_tokens": 800,   # longer narrative response with status blocks
        "probability": 1.0,
        "note": "System prompt (18KB rule file) + prologue + past records + 15 recent logs + user input",
    },
}


def print_separator(char="─", length=80):
    print(char * length)


def calculate_service(name: str, calls: dict, turns_per_session: int, sessions_per_day: int, days: int = 30):
    """Calculate and display costs for a service."""
    print(f"\n{'=' * 80}")
    print(f"  {name}")
    print(f"{'=' * 80}")

    # Per-turn breakdown
    print(f"\n{'Per-Turn Breakdown':^80}")
    print_separator()
    print(f"{'Call':<50} {'Model':<25} {'Input':>7} {'Output':>7} {'Prob':>5} {'Cost ($)':>10}")
    print_separator()

    total_per_turn = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    for call_name, info in calls.items():
        c = cost(info["model"], info["input_tokens"], info["output_tokens"])
        effective_cost = c * info["probability"]
        effective_input = int(info["input_tokens"] * info["probability"])
        effective_output = int(info["output_tokens"] * info["probability"])
        total_per_turn += effective_cost
        total_input_tokens += effective_input
        total_output_tokens += effective_output
        print(
            f"  {call_name:<48} {info['model']:<25} "
            f"{effective_input:>6} {effective_output:>6} "
            f"{info['probability']:>4.0%} "
            f"${effective_cost:>9.6f}"
        )

    print_separator()
    print(f"  {'TOTAL PER TURN':<48} {'':25} {total_input_tokens:>6} {total_output_tokens:>6} {'':>5} ${total_per_turn:>.6f}")

    # Per-session
    cost_per_session = total_per_turn * turns_per_session
    tokens_per_session = (total_input_tokens + total_output_tokens) * turns_per_session

    # Daily
    cost_per_day_per_user = cost_per_session * sessions_per_day
    cost_per_day_total = cost_per_day_per_user  # per-user basis

    # Monthly (per user)
    cost_per_month = cost_per_day_total * days

    print(f"\n{'Aggregated Estimates':^80}")
    print_separator()
    print(f"  Assumptions: {turns_per_session} turns/session, {sessions_per_day} sessions/day/user, {days} days/month")
    print_separator()
    print(f"  {'Metric':<45} {'Tokens':>12} {'Cost (USD)':>15}")
    print_separator()
    print(f"  {'Per turn':<45} {total_input_tokens + total_output_tokens:>12,} ${total_per_turn:>14.6f}")
    print(f"  {'Per session ({} turns)'.format(turns_per_session):<45} {tokens_per_session:>12,} ${cost_per_session:>14.4f}")
    print(f"  {'Per day/user ({} sessions)'.format(sessions_per_day):<45} {tokens_per_session * sessions_per_day:>12,} ${cost_per_day_per_user:>14.4f}")
    print(f"  {'Per month/user ({} days)'.format(days):<45} {tokens_per_session * sessions_per_day * days:>12,} ${cost_per_month:>14.4f}")
    print_separator()

    return total_per_turn, total_input_tokens, total_output_tokens


def main():
    print("\n" + "█" * 80)
    print(f"{'CHATTING SERVICE COST CALCULATOR':^80}")
    print("█" * 80)

    # ── Pricing Table ──
    print(f"\n{'Model Pricing (per 1M tokens)':^80}")
    print_separator()
    print(f"  {'Model':<30} {'Input ($/1M)':>15} {'Output ($/1M)':>15}")
    print_separator()
    for model, p in PRICING.items():
        print(f"  {model:<30} ${p['input']:>13.2f} ${p['output']:>13.2f}")
    print_separator()

    # ── Hari Chat Service ──
    hari_per_turn, hari_in, hari_out = calculate_service(
        name="HARI CHAT SERVICE (OpenAI)",
        calls=HARI_CALLS,
        turns_per_session=20,
        sessions_per_day=2,
        days=30,
    )

    # ── RPG Roleplay Service ──
    rpg_per_turn, rpg_in, rpg_out = calculate_service(
        name="RPG ROLEPLAY SERVICE (Google Gemini)",
        calls=RPG_CALLS,
        turns_per_session=30,    # RPG sessions tend to be longer
        sessions_per_day=1,
        days=30,
    )

    # ── Combined Summary ──
    print(f"\n{'=' * 80}")
    print(f"{'COMBINED MONTHLY COST PROJECTION':^80}")
    print(f"{'=' * 80}")
    print_separator()
    print(f"  {'Scenario':<45} {'Hari':>10} {'RPG':>10} {'Total':>12}")
    print_separator()

    for n_users in [10, 50, 100, 500, 1000]:
        hari_monthly = hari_per_turn * 20 * 2 * 30 * n_users
        rpg_monthly = rpg_per_turn * 30 * 1 * 30 * n_users
        total = hari_monthly + rpg_monthly
        print(f"  {f'{n_users:,} users':<45} ${hari_monthly:>9.2f} ${rpg_monthly:>9.2f} ${total:>11.2f}")

    print_separator()

    # ── Per-turn KRW ──
    KRW_RATE = 1380  # approximate USD/KRW
    print(f"\n{f'Korean Won (KRW) Reference (1 USD ≈ {KRW_RATE:,} KRW)':^80}")
    print_separator()
    print(f"  {'Metric':<50} {'USD':>12} {'KRW':>14}")
    print_separator()
    print(f"  {'Hari: per turn':<50} ${hari_per_turn:>11.6f} ₩{hari_per_turn * KRW_RATE:>13.2f}")
    print(f"  {'Hari: per session (20 turns)':<50} ${hari_per_turn * 20:>11.4f} ₩{hari_per_turn * 20 * KRW_RATE:>13.2f}")
    print(f"  {'Hari: per month/user':<50} ${hari_per_turn * 20 * 2 * 30:>11.4f} ₩{hari_per_turn * 20 * 2 * 30 * KRW_RATE:>13.0f}")
    print(f"  {'RPG: per turn':<50} ${rpg_per_turn:>11.6f} ₩{rpg_per_turn * KRW_RATE:>13.2f}")
    print(f"  {'RPG: per session (30 turns)':<50} ${rpg_per_turn * 30:>11.4f} ₩{rpg_per_turn * 30 * KRW_RATE:>13.2f}")
    print(f"  {'RPG: per month/user':<50} ${rpg_per_turn * 30 * 1 * 30:>11.4f} ₩{rpg_per_turn * 30 * 1 * 30 * KRW_RATE:>13.0f}")
    print_separator()

    print("\n* Token estimates are based on actual code analysis of system prompts,")
    print("  memory contexts, and LLM call patterns in the codebase.")
    print("* Probabilities reflect regex prefilters and conditional call paths.")
    print("* Actual costs may vary based on conversation length and caching.\n")


if __name__ == "__main__":
    main()
