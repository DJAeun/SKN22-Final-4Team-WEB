import re
import os
from pathlib import Path
from django.template import Template, Context
from django.conf import settings
from .models import RpgSession, RpgChatLog, RpgHyperMemory, RpgLorebook

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
        
        # 2. Prologue (Lorebook & Setting)
        # Assuming higher priority number means it should be injected closer to the end, or just grouped.
        lorebooks = RpgLorebook.objects.filter(is_active=True).order_by('priority').values_list('lorebook', flat=True)
        prologue_text = "\n\n".join(lorebooks)
        
        # 3. Past Records (HyperMemory)
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
        recent_records_text = "\n".join([f"{log.role}: {log.content}" for log in recent_logs])
        if not recent_records_text:
            recent_records_text = "(No recent records)"
        
        # 5. Starting Point (User Input)
        # TODO: Implement optional Vector DB RAG injection here
        starting_point_text = f"User ({self.session.user_nickname}) Action/Dialogue: {user_input}"
        
        # Sandwich everything
        final_prompt = f"{system_base}\n\n"
        final_prompt += f"[Prologue]\n{prologue_text}\n\n"
        final_prompt += f"[Past Records]\n{past_records_text}\n\n"
        final_prompt += f"[Recent Records]\n{recent_records_text}\n\n"
        final_prompt += f"[Starting Point]\n{starting_point_text}\n"
        
        return final_prompt

from google import genai
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
        # Save user input to chat log immediately
        RpgChatLog.objects.create(session=self.session, role=self.session.user_nickname, content=user_input)

        prompt = self.builder.assemble_final_prompt(user_input)
        
        # Invoke LLM natively
        response = self.client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents=prompt,
        )
        raw_text = response.text
        
        # Parse Status Block (Stress, Crack Stage)
        import re
        stress_match = re.search(r'Stress:\s*(\d+)%', raw_text, re.IGNORECASE)
        stage_match = re.search(r'Crack Stage:\s*Stage\s*(\d+)', raw_text, re.IGNORECASE)
        fields_to_update = []
        if stress_match:
            self.session.stress = int(stress_match.group(1))
            fields_to_update.append('stress')
        if stage_match:
            self.session.crack_stage = int(stage_match.group(1))
            fields_to_update.append('crack_stage')
            
        if fields_to_update:
            self.session.save(update_fields=fields_to_update)

        # Parse <Revision>...</Revision>
        parsed_content = self._parse_revision(raw_text)

        # Save LLM output to chat log
        with transaction.atomic():
            new_log = RpgChatLog.objects.create(
                session=self.session,
                role="NPC Engine",  # Needs to extract actual character name later or keep generic
                raw_content=raw_text,
                content=parsed_content,
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

        return {
            'content': parsed_content,
            'raw': raw_text
        }

    def _parse_revision(self, text: str) -> str:
        """
        Extracts content inside <Revision> block.
        Fallback to whole text if not found.
        """
        import re
        match = re.search(r'<Revision>(.*?)</Revision>', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback handles the cases where LLM forgets the tag
        return text.strip()
