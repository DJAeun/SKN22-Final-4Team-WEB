from __future__ import annotations

from django.template import Context, Template


def has_final_consonant(text: str) -> bool:
    cleaned = (text or "").strip()
    if not cleaned:
        return False

    last_char = cleaned[-1]
    code = ord(last_char)
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0

    return False


def attach_josa(text: str, with_batchim: str, without_batchim: str) -> str:
    return f"{text}{with_batchim if has_final_consonant(text) else without_batchim}"


def build_user_placeholder_context(nickname: str) -> dict[str, str]:
    return {
        "user": nickname,
        "User": nickname,
        "user_nickname": nickname,
        "user_subj": attach_josa(nickname, "이", "가"),
        "user_obj": attach_josa(nickname, "을", "를"),
        "user_topic": attach_josa(nickname, "은", "는"),
        "user_with": attach_josa(nickname, "과", "와"),
        "user_and": attach_josa(nickname, "이랑", "랑"),
    }


def render_user_template(text: str, nickname: str, extra_context: dict | None = None) -> str:
    context = build_user_placeholder_context(nickname)
    if extra_context:
        context.update(extra_context)

    return Template(text).render(Context(context))
