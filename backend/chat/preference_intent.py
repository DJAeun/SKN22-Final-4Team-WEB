"""
preference_intent.py
────────────────────
Detects, per user message, whether the user is telling Hari:
  - what tone to use (반말/존댓말),
  - what honorific to call them by (오빠/언니/형/누나/선배/custom/none),
  - their name.

Two-stage detection to keep cost near zero on typical chat:
  1. Cheap regex prefilter — only fires on phrases that plausibly express a preference.
  2. LLM confirmation via `with_structured_output(PreferenceIntent)` using gpt-4o-mini.

The caller (engine.get_response) only acts on results where confidence == "high"
AND at least one field is non-null.
"""
import logging
import re
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PreferenceIntent(BaseModel):
    tone: Optional[str] = Field(
        default=None,
        description='"casual" for 반말, "formal" for 존댓말, null if not expressed.',
    )
    title: Optional[str] = Field(
        default=None,
        description=(
            'The honorific the user wants Hari to call them by '
            '(e.g. "오빠", "언니", "형", "누나", "선배", "사장님"). '
            'Empty string "" means the user explicitly asked to clear the title '
            '(e.g. "그냥 이름만 불러"). null if not expressed.'
        ),
    )
    name: Optional[str] = Field(
        default=None,
        description="The proper name the user just stated for themselves. null if not expressed.",
    )
    confidence: str = Field(
        default="low",
        description='"high" only when the user clearly and directly asked in this message. Otherwise "low".',
    )


# ── Stage 1: regex prefilter ──────────────────────────────────────────────────
#
# These regexes are intentionally over-inclusive — false positives are fine
# because the LLM confirmation stage filters them out. False negatives are bad
# because they skip the LLM entirely and lose the signal.

_TONE_CASUAL = re.compile(r"(반말|말.{0,2}놔|말.{0,3}편하게|편하게.{0,3}해|편하게.{0,3}말)")
_TONE_FORMAL = re.compile(r"(존댓말|존대|높임말)")

_TITLE_TOKENS = r"(오빠|언니|형|누나|선배|누님|형님|사장님|대장|주인님)"
_TITLE_PICK = re.compile(
    rf"({_TITLE_TOKENS}.{{0,8}}(불러|해|라고|야|이야|임))|"
    rf"(나.{{0,3}}{_TITLE_TOKENS}(야|이야|임))|"
    rf"({_TITLE_TOKENS}.{{0,10}}(줘|달라|주세요))"
)
_TITLE_CLEAR = re.compile(r"(이름.{0,3}(만|으로).{0,3}(불러|해))|(호칭.{0,3}(빼|없|떼))")

_NAME_STATEMENT = re.compile(
    r"(내.{0,2}이름.{0,3}(은|는))|"
    r"(나.{0,3}[가-힣A-Za-z]{1,10}(이야|야|입니다|예요|이에요))|"
    r"(저.{0,3}[가-힣A-Za-z]{1,10}(입니다|이에요|예요|라고.{0,3}합니다))"
)


def _regex_prefilter(user_input: str) -> bool:
    """Return True if the message plausibly expresses a tone/title/name preference."""
    if not user_input:
        return False
    text = user_input.strip()
    # Very short bare-name replies (e.g. "민제", "나 준호야") also count —
    # the onboarding flow relies on the LLM confirming these.
    if len(text) <= 12 and re.fullmatch(r"[가-힣A-Za-z]{1,10}", text):
        return True
    return bool(
        _TONE_CASUAL.search(text)
        or _TONE_FORMAL.search(text)
        or _TITLE_PICK.search(text)
        or _TITLE_CLEAR.search(text)
        or _NAME_STATEMENT.search(text)
    )


# ── Stage 2: LLM confirmation ─────────────────────────────────────────────────

_CLASSIFIER_SYSTEM_PROMPT = """\
You extract explicit preferences from a single Korean chat message that a user sent to an AI friend named Hari (하리).

You must extract ONLY what the user explicitly requested in *this* message.
Do NOT infer from context, do NOT guess, do NOT fill in defaults.
When unsure, return null for that field.

Fields:
- tone: "casual" if the user asked Hari to use 반말 / speak casually.
        "formal" if the user asked Hari to use 존댓말 / speak politely.
        null otherwise.
- title: the honorific the user wants Hari to call THEM by (not Hari's own title).
         Examples: "오빠", "언니", "형", "누나", "선배", "사장님", "대장".
         Use "" (empty string) ONLY when the user explicitly said to drop the honorific
         (e.g. "그냥 이름만 불러", "호칭 빼고 불러").
         null if the user did not ask about their honorific in this message.
- name: the proper name the user just stated for themselves.
        Accept a bare name reply like "민제" or "나 준호야" — in an onboarding context
        this counts as the user telling Hari their name.
        null if no name was stated.
- confidence: "high" only when the user directly and unambiguously requested the change
              in this message. Otherwise "low".

Critical false-positive guards — return null / "low" for these:
- "우리 형이 그랬는데" → the user is talking ABOUT their brother, not asking to be called 형.
- "오빠한테 물어봤어" → talking about someone else.
- "존댓말 쓰는 사람 싫어" → an opinion, not a request.
- Any message that merely mentions an honorific in passing without a request verb
  (불러/해/라고/줘/달라) directed at Hari.

Return the structured output.\
"""


def extract_preference_intent(user_input: str) -> Optional[PreferenceIntent]:
    """
    Returns a PreferenceIntent when the user message plausibly expresses a preference,
    None when the regex prefilter rejects it (the common case — no LLM call made).

    The caller must still check `confidence == "high"` and that at least one of
    tone/title/name is non-null before acting.
    """
    if not _regex_prefilter(user_input):
        return None

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=3)
        structured_llm = llm.with_structured_output(PreferenceIntent)

        result = structured_llm.invoke([
            SystemMessage(content=_CLASSIFIER_SYSTEM_PROMPT),
            HumanMessage(content=user_input),
        ])

        logger.info(
            "Preference intent: tone=%s title=%s name=%s confidence=%s",
            result.tone, result.title, result.name, result.confidence,
        )
        return result

    except Exception as e:
        logger.error("Preference intent extraction failed: %s", e, exc_info=True)
        return None
