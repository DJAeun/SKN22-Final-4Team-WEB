import re
import os
from pathlib import Path
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from .models import RpgSession, RpgChatLog, RpgHyperMemory, RpgLorebook, RpgCharacterImage
from .korean_text import build_user_placeholder_context


IMAGE_COMMAND_PATTERN = re.compile(r'<img="([a-z0-9_]+)">', re.IGNORECASE)
ALLOWED_IMAGE_CLOTHES = {'suit', 'daily', 'baking'}
ALLOWED_IMAGE_EMOTIONS = {
    'serious', 'depressed', 'angry', 'aroused', 'bored', 'curious', 'disgust',
    'embarrassed', 'excited', 'happy', 'nervous', 'neutral',
    'panic', 'pout', 'proud', 'sad', 'sleepy', 'smug', 'surprised', 'thinking',
    'worried',
}
FIRST_MESSAGE_KEYWORDS = {'firstmessage', 'first message'}
SECTION_NAMES = ('Planning', 'Draft', 'Review', 'Revision')


def normalize_lorebook_keywords(raw_keywords) -> list[str]:
    if raw_keywords is None:
        return []

    if isinstance(raw_keywords, str):
        stripped = raw_keywords.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            stripped = stripped[1:-1]
        keywords = [part.strip() for part in stripped.split(',')]
    elif isinstance(raw_keywords, (list, tuple, set)):
        keywords = [str(part).strip() for part in raw_keywords]
    else:
        keywords = [str(raw_keywords).strip()]

    return [keyword for keyword in keywords if keyword]


def keyword_matches_text(keyword: str, text: str) -> bool:
    normalized_keyword = keyword.casefold()
    normalized_text = text.casefold()
    return normalized_keyword in normalized_text if normalized_keyword else False


def is_first_message_keywords(raw_keywords) -> bool:
    normalized_keywords = normalize_lorebook_keywords(raw_keywords)
    return any(keyword.casefold() in FIRST_MESSAGE_KEYWORDS for keyword in normalized_keywords)


def get_first_message_lorebook() -> RpgLorebook | None:
    lorebooks = RpgLorebook.objects.filter(is_active=True).order_by('priority', 'created_at')
    for lorebook in lorebooks:
        if is_first_message_keywords(lorebook.keywords):
            return lorebook
    return None


def _extract_meta_value(source_text: str, label: str) -> str:
    patterns = [
        rf'{label}:\s*(.+?)(?=\s*\|\s*[A-Za-z ]+:|\s*\]|\n|$)',
        rf'^{label}:\s*(.+)$',
    ]

    for pattern in patterns:
        match = re.search(pattern, source_text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            return normalize_meta_text(match.group(1))

    return ''


def extract_status_metadata(text: str) -> dict:
    status_block_match = re.search(r'<Status>(.*?)</Status>', text, re.DOTALL | re.IGNORECASE)
    source_text = status_block_match.group(1) if status_block_match else text

    stress_value = _extract_meta_value(source_text, 'Stress')
    stress_match = re.search(r'(\d+)', stress_value)

    stage_value = _extract_meta_value(source_text, 'Crack Stage')
    stage_match = re.search(r'(\d+)', stage_value, re.IGNORECASE)

    thought = ''
    for label in ['Current Thought', 'Inner Thought', 'Thought']:
        thought = _extract_meta_value(source_text, label)
        if thought:
            break

    return {
        'date': _extract_meta_value(source_text, 'Date'),
        'time': _extract_meta_value(source_text, 'Time'),
        'location': _extract_meta_value(source_text, 'Location'),
        'stress': int(stress_match.group(1)) if stress_match else None,
        'crack_stage': int(stage_match.group(1)) if stage_match else None,
        'thought': thought,
    }


def normalize_meta_text(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r'^[\s\[\]\(\)\{\}",\'`]+', '', cleaned)
    cleaned = re.sub(r'[\s\[\]\(\)\{\}",\'`]+$', '', cleaned)
    cleaned = re.sub(r'^\s*-\s*', '', cleaned)
    return cleaned.strip()


def extract_named_section(text: str, name: str) -> str:
    tag_patterns = [
        rf'<\s*{name}\s*>(.*?)</\s*{name}\s*>',
        rf'<\s*{name}\s*>(.*)$',
    ]

    for pattern in tag_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    heading_pattern = rf'(?ims)^\s*#{{0,6}}\s*{name}\s*:?\s*$\s*(.*?)(?=^\s*#{{0,6}}\s*(?:{"|".join(SECTION_NAMES)})\s*:?\s*$|\Z)'
    heading_match = re.search(heading_pattern, text)
    if heading_match:
        return heading_match.group(1).strip()

    return ''


def remove_named_section(text: str, name: str) -> str:
    cleaned = re.sub(
        rf'<\s*{name}\s*>.*?</\s*{name}\s*>',
        '',
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    cleaned = re.sub(
        rf'(?ims)^\s*#{{0,6}}\s*{name}\s*:?\s*$\s*.*?(?=^\s*#{{0,6}}\s*(?:{"|".join(SECTION_NAMES)})\s*:?\s*$|\Z)',
        '',
        cleaned,
    )
    return cleaned


def strip_status_content(text: str) -> str:
    cleaned = re.sub(r'<Status>.*?</Status>', '', text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(
        r'<\s*Status\s*>\s*\[\s*Date:.*?(?:Thought|Inner Thought|Current Thought)\s*:\s*.*?\]\s*</\s*Status\s*>',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r'\[\s*Date:.*?(?:Thought|Inner Thought|Current Thought)\s*:\s*.*?\]',
        '',
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )
    cleaned = re.sub(
        r'^[\s\[\]\(\)\{\}",\'`-]*(Stress|Crack Stage|Current Thought|Inner Thought|Thought|Location|Date|Time)\s*:\s*.*$',
        '',
        cleaned,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    cleaned = re.sub(r'</?(Planning|Draft|Review|Revision)>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\s*#{0,6}\s*(Planning|Draft|Review|Revision)\s*:?\s*$', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r'^\s*`{2,}\s*', '', cleaned)
    cleaned = re.sub(r'(?m)^\s*`{2,}\s*$', '', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def extract_image_command(text: str) -> str:
    match = IMAGE_COMMAND_PATTERN.search(text)
    if not match:
        return ''
    return match.group(1).strip().lower()


def strip_image_command(text: str) -> str:
    cleaned = IMAGE_COMMAND_PATTERN.sub('', text)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def sanitize_fallback_story_text(text: str) -> str:
    cleaned = text or ''
    cleaned = re.sub(r'<Status>.*?</Status>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = remove_named_section(cleaned, 'Planning')
    cleaned = remove_named_section(cleaned, 'Review')
    cleaned = remove_named_section(cleaned, 'Draft')
    cleaned = remove_named_section(cleaned, 'Revision')
    cleaned = re.sub(r'</?(Planning|Draft|Review|Revision)>', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'^\s*#{0,6}\s*(Planning|Draft|Review|Revision)\s*:?\s*$', '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return strip_status_content(cleaned)


def get_context_safe_content(text: str) -> str:
    return strip_image_command(text or '')


def parse_image_command(command: str) -> tuple[str, str] | None:
    clothes, separator, emotion = command.partition('_')
    if not separator or not clothes or not emotion:
        return None
    return clothes.lower(), emotion.lower()


def get_latest_image_command_for_session(session: RpgSession) -> str:
    latest_command = (
        RpgChatLog.objects.filter(session=session, role='NPC Engine')
        .exclude(image_command__isnull=True)
        .exclude(image_command__exact='')
        .order_by('-id')
        .values_list('image_command', flat=True)
        .first()
    )
    return (latest_command or '').strip().lower()


def resolve_image_metadata(session: RpgSession, text: str) -> dict:
    command = extract_image_command(text)
    if not command:
        return {}

    parsed = parse_image_command(command)
    if not parsed:
        return {}

    clothes, emotion = parsed
    if clothes not in ALLOWED_IMAGE_CLOTHES or emotion not in ALLOWED_IMAGE_EMOTIONS:
        return {}

    if get_latest_image_command_for_session(session) == command:
        return {}

    matched_image = (
        RpgCharacterImage.objects.filter(
            clothes=clothes,
            emotion=emotion,
            is_active=True,
        )
        .order_by('-created_at')
        .first()
    )
    if not matched_image:
        return {}

    return {
        'image_command': command,
        'image_url': matched_image.image_url,
    }


def apply_status_metadata_to_session(session: RpgSession, status_metadata: dict) -> None:
    fields_to_update = []

    if status_metadata.get('stress') is not None:
        session.stress = status_metadata['stress']
        fields_to_update.append('stress')
    if status_metadata.get('crack_stage') is not None:
        session.crack_stage = status_metadata['crack_stage']
        fields_to_update.append('crack_stage')

    session.updated_at = timezone.now()
    fields_to_update.append('updated_at')
    session.save(update_fields=fields_to_update)


def build_status_snapshot(status_metadata: dict) -> dict:
    return {
        'date': normalize_meta_text(status_metadata.get('date', '')),
        'time': normalize_meta_text(status_metadata.get('time', '')),
        'location': normalize_meta_text(status_metadata.get('location', '')),
        'stress': status_metadata.get('stress'),
        'crack_stage': status_metadata.get('crack_stage'),
        'thought': normalize_meta_text(status_metadata.get('thought', '')),
    }


def get_latest_status_snapshot_for_session(session: RpgSession) -> dict:
    latest_engine_log = (
        RpgChatLog.objects.filter(session=session, role='NPC Engine')
        .exclude(raw_content__isnull=True)
        .exclude(raw_content__exact='')
        .order_by('-id')
        .first()
    )
    if not latest_engine_log:
        return build_status_snapshot({})

    if latest_engine_log.status_snapshot:
        return latest_engine_log.status_snapshot

    return build_status_snapshot(extract_status_metadata(latest_engine_log.raw_content))

class PromptBuilder:
    def __init__(self, session: RpgSession):
        self.session = session
        # Define paths
        self.project_root = settings.BASE_DIR.parent
        self.rule_file_path = self.project_root / 'backend' / 'roleplay' / 'prompts' / 'llm_rule.md'
        
    def _convert_risu_to_django_template(self, text: str) -> str:
        """
        Converts RisuAI macros into Django Template syntax.
        Replace getglobalvar::toggle_... with simpler python variable names.
        """
        # Replace {{user}} with django templating syntax if we pass user_nickname
        text = text.replace('{{user}}', '{{ user_nickname }}')
        text = text.replace('{{User}}', '{{ user_nickname }}')
        
        # We handle the specific if_pure conditional blocks.
        # Example: {{#if_pure {{? {{getglobalvar::toggle_상태창}}=1}}}} ... {{/if_pure}}
        
        # 1. 상태창 (toggle_status_window)
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_상태창}}=1}}}}', '{% if toggle_status_window == 1 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_상태창}}=0}}}}', '{% if toggle_status_window == 0 %}')
        
        # 2. 시점 (toggle_perspective)
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_시점}}=0}}}}', '{% if toggle_perspective == 0 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_시점}}=1}}}}', '{% if toggle_perspective == 1 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_시점}}=2}}}}', '{% if toggle_perspective == 2 %}')
        
        # 3. 사칭 (toggle_impersonation)
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_사칭}}=0}}}}', '{% if toggle_impersonation == 0 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_사칭}}=1}}}}', '{% if toggle_impersonation == 1 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_사칭}}=2}}}}', '{% if toggle_impersonation == 2 %}')
        
        # 4. 시도 (toggle_attempt)
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_시도}}=0}}}}', '{% if toggle_attempt == 0 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_시도}}=1}}}}', '{% if toggle_attempt == 1 %}')
        
        # 5. 인풋사칭 (toggle_input_impersonation)
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_인풋사칭}}=0}}}}', '{% if toggle_input_impersonation == 0 %}')
        text = text.replace('{{#if_pure {{? {{getglobalvar::toggle_인풋사칭}}=1}}}}', '{% if toggle_input_impersonation == 1 %}')

        # Close all if_pure blocks
        text = text.replace('{{/if_pure}}', '{% endif %}')
        return text

    def _build_template_context(self, kwargs: dict) -> dict:
        status_toggle = 1 if self.session.status_window_enabled else 0
        context_dict = build_user_placeholder_context(self.session.user_nickname)
        context_dict.update({
            'toggle_status_window': status_toggle,
            'toggle_perspective': kwargs.get('perspective', 1),
            'toggle_impersonation': kwargs.get('impersonation', 1),
            'toggle_attempt': kwargs.get('attempt', 0),
            'toggle_input_impersonation': kwargs.get('input_impersonation', 0),
        })
        return context_dict

    def _render_template_text(self, text: str, kwargs: dict) -> str:
        return Template(text).render(Context(self._build_template_context(kwargs)))

    def _build_lorebook_lookup_corpus(self, user_input: str, recent_records_text: str, latest_memory: RpgHyperMemory | None) -> str:
        corpus_parts = [user_input, recent_records_text]

        if latest_memory:
            corpus_parts.extend([
                latest_memory.location_transition or '',
                latest_memory.context_overview or '',
                latest_memory.emotional_dynamics or '',
                "\n".join(latest_memory.events or []),
                "\n".join(latest_memory.infos or []),
                "\n".join(latest_memory.dialogues or []),
                ", ".join(latest_memory.characters_present or []),
            ])

        return "\n".join(part for part in corpus_parts if part).casefold()

    def _select_lorebook_texts(
        self,
        user_input: str,
        recent_records_text: str,
        latest_memory: RpgHyperMemory | None,
        kwargs: dict,
    ) -> list[str]:
        lorebooks = RpgLorebook.objects.filter(is_active=True).order_by('priority', 'created_at')
        lookup_corpus = self._build_lorebook_lookup_corpus(user_input, recent_records_text, latest_memory)
        selected_texts: list[str] = []
        first_message_text = ''

        for lorebook in lorebooks:
            rendered_text = self._render_template_text(lorebook.lorebook, kwargs)
            normalized_keywords = normalize_lorebook_keywords(lorebook.keywords)

            if is_first_message_keywords(normalized_keywords):
                first_message_text = rendered_text
                continue

            if lorebook.is_constant:
                selected_texts.append(rendered_text)
                continue

            if normalized_keywords and any(keyword_matches_text(keyword, lookup_corpus) for keyword in normalized_keywords):
                selected_texts.append(rendered_text)

        if first_message_text:
            return [first_message_text, *selected_texts]
        return selected_texts
    def build_system_prompt(self, kwargs: dict) -> str:
        """
        Loads the rule markdown, converts macros to Django templating, 
        and renders it with Context.
        Kwargs allow passing default settings not covered in the DB schema.
        """
        if not self.rule_file_path.exists():
            return "Base rule file missing."

        raw_text = self.rule_file_path.read_text(encoding='utf-8')
        django_template_str = self._convert_risu_to_django_template(raw_text)
        return self._render_template_text(django_template_str, kwargs)
        
        t = Template(django_template_str)
        
        # status_window_enabled maps to 1 if True else 0.
        status_toggle = 1 if self.session.status_window_enabled else 0
        
        context_dict = {
            'user_nickname': self.session.user_nickname,
            'toggle_status_window': status_toggle,
            'toggle_perspective': kwargs.get('perspective', 1), # default 1: 2nd person (당신)
            'toggle_impersonation': kwargs.get('impersonation', 1), # default 1
            'toggle_attempt': kwargs.get('attempt', 0), # default 0
            'toggle_input_impersonation': kwargs.get('input_impersonation', 0) # default 0
        }
        
        c = Context(context_dict)
        return t.render(c)

    def assemble_final_prompt(self, user_input: str, kwargs: dict = {}) -> str:
        """
        Assembles System + Prologue + Past Records + Recent Records + Starting Point.
        """
        # 1. System Prompt (llm_rule.md)
        system_base = self.build_system_prompt(kwargs)

        # 2. Past Records (HyperMemory)
        # Fetch latest hyper memory for the session
        latest_memory = RpgHyperMemory.objects.filter(session=self.session).order_by('-created_at').first()
        past_records_text = ""
        if latest_memory:
            past_records_text += f"Time and Place: {latest_memory.in_game_date} {latest_memory.in_game_time} {latest_memory.location_transition}\n"
            past_records_text += f"Characters: {', '.join(latest_memory.characters_present)}\n"
            past_records_text += f"Context: {latest_memory.context_overview}\n"
            past_records_text += f"Events: {latest_memory.events}\n"
            past_records_text += f"Infos: {latest_memory.infos}\n"
            past_records_text += f"Emotions: {latest_memory.emotional_dynamics}\n"
            past_records_text += f"Dialogues: {latest_memory.dialogues}\n"
        else:
            past_records_text = "(No past records)"
        
        # 4. Recent Records (Chat Logs)
        # Fetch last 15 messages for short-term memory STM
        recent_logs = RpgChatLog.objects.filter(session=self.session).order_by('-created_at')[:15]
        # Revese to chronological order
        recent_logs = reversed(recent_logs)
        recent_records_text = "\n".join(
            [f"{log.role}: {get_context_safe_content(log.content)}" for log in recent_logs]
        )
        if not recent_records_text:
            recent_records_text = "(No recent records)"

        # 4. Prologue (always-on lorebooks + keyword-triggered lorebooks + canonical first message)
        rendered_lorebooks = self._select_lorebook_texts(
            user_input=user_input,
            recent_records_text=recent_records_text,
            latest_memory=latest_memory,
            kwargs=kwargs,
        )
        prologue_text = "\n\n".join(rendered_lorebooks)
        if not prologue_text:
            prologue_text = "(No prologue)"
        
        # 5. Starting Point (User Input)
        # TODO: Implement optional Vector DB RAG injection here
        current_portrait = get_latest_image_command_for_session(self.session) or "(none)"
        starting_point_text = f"User ({self.session.user_nickname}) Action/Dialogue: {user_input}"
        
        # Sandwich everything
        final_prompt = f"{system_base}\n\n"
        final_prompt += f"[Prologue]\n{prologue_text}\n\n"
        final_prompt += f"[Past Records]\n{past_records_text}\n\n"
        final_prompt += f"[Recent Records]\n{recent_records_text}\n\n"
        final_prompt += f"[Current Portrait]\n{current_portrait}\n\n"
        final_prompt += f"[Starting Point]\n{starting_point_text}\n"
        
        return final_prompt

from google import genai
from google.genai import types

import os
from django.db import transaction

class MainEngine:
    def __init__(self, session: RpgSession):
        self.session = session
        self.builder = PromptBuilder(session)
        # Using Google GenAI SDK native client
        self.client = genai.Client()

    def generate_response(self, user_input: str) -> dict:
        """
        Receives user input, builds the prompt, invokes LLM, and parses output.
        """
        # Save user input to chat log immediately with the latest known story-state snapshot
        RpgChatLog.objects.create(
            session=self.session,
            role=self.session.user_nickname,
            content=user_input,
            status_snapshot=get_latest_status_snapshot_for_session(self.session),
        )

        prompt = self.builder.assemble_final_prompt(user_input)
        
        # Invoke LLM natively with relaxed safety settings
        response = self.client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                safety_settings=[
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                    types.SafetySetting(
                        category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                        threshold=types.HarmBlockThreshold.BLOCK_NONE,
                    ),
                ],
                temperature=1.0,
            )
        )
        raw_text = response.text
        
        # Parse Status Block (Date, Time, Location, Stress, Crack Stage, Thought)
        status_metadata = extract_status_metadata(raw_text)
        apply_status_metadata_to_session(self.session, status_metadata)
        status_snapshot = build_status_snapshot(status_metadata)
        image_metadata = resolve_image_metadata(self.session, raw_text)

        # Parse <Revision>...</Revision>
        parsed_content = self._parse_revision(raw_text)

        # Save LLM output to chat log
        with transaction.atomic():
            new_log = RpgChatLog.objects.create(
                session=self.session,
                role="NPC Engine",  # Needs to extract actual character name later or keep generic
                raw_content=raw_text,
                content=parsed_content,
                status_snapshot=status_snapshot,
                image_command=image_metadata.get('image_command'),
                image_url=image_metadata.get('image_url'),
                token_count=len(raw_text) // 4  # rough heuristic, better to count properly if possible
            )
            
            # Update session total tokens
            self.session.total_tokens += new_log.token_count
            self.session.save(update_fields=['total_tokens'])

            from .tasks import run_embedding_task, run_hypermemory_task
            
            try:
                run_embedding_task.delay(new_log.id)
            except Exception as e:
                import logging
                logging.warning(f"[Roleplay] Celery embedding task failed (non-critical): {e}")
            
            # If tokens cross threshold, update memory and reset counter
            if self.session.total_tokens > 200:
                try:
                    run_hypermemory_task.delay(str(self.session.id))
                except Exception as e:
                    import logging
                    logging.warning(f"[Roleplay] Celery hypermemory task failed (non-critical): {e}")
                self.session.total_tokens = 0
                self.session.save(update_fields=['total_tokens'])

            self._touch_session()

        return {
            'content': parsed_content,
            'raw': raw_text,
            'status_snapshot': status_snapshot,
            'image_command': image_metadata.get('image_command'),
            'image_url': image_metadata.get('image_url'),
        }

    def _touch_session(self) -> None:
        self.session.updated_at = timezone.now()
        self.session.save(update_fields=['updated_at'])

    def _parse_revision(self, text: str) -> str:
        """
        Extracts content inside <Revision> block.
        Fallback to whole text if not found.
        """
        revision_text = extract_named_section(text, 'Revision')
        if revision_text:
            return strip_status_content(revision_text)

        draft_text = extract_named_section(text, 'Draft')
        if draft_text:
            return strip_status_content(draft_text)
        # Fallback keeps only story-safe content and drops Planning/Review noise.
        return sanitize_fallback_story_text(text.strip())
