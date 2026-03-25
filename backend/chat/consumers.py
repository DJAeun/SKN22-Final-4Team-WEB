import asyncio
import json
import logging
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import connection
from django.utils import timezone
from .models import Message, ChatMemory

logger = logging.getLogger(__name__)

# First-time greeting (no name known yet)
_FIRST_GREETING = '안녕!! 난 하리야. 넌 이름이 뭐야?'

# Returning user greetings — {name} will be replaced with the user's name
_RETURNING_GREETINGS = [
    '오 {name} 왔어!! 오늘 뭐 했어?',
    '{name}!! 보고 싶었어ㅋㅋ 무슨 일이야?',
    '어 {name}! 오늘 기분 어때?',
    '{name} 왔네~ 오늘은 무슨 얘기 할까?',
    '오 {name}~ 요즘 어떻게 지내?',
    '{name}! 심심했는데 잘 왔어ㅋㅋ',
    '어 왔어 {name}! 나 진짜 심심했거든',
]

# Returning user but name unknown
_RETURNING_NO_NAME_GREETINGS = [
    '어 왔어!! 오늘 뭐 했어?',
    '오 또 왔네ㅋㅋ 반가워! 오늘은 무슨 얘기 할까?',
    '왔어?? 나 심심했는데 잘 왔어',
    '어 반가워~ 오늘 기분 어때?',
]

# Trigger Hari persona enrichment every N completed conversations per user
PERSONA_UPDATE_INTERVAL = 20



class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            user = self.scope["user"]

            if not user.is_authenticated:
                await self.close(code=4401)
                return

            self.session_messages = []
            self.user_id = user.id
            self.thread_id = str(user.id)
            self.anonymous_id = None

            self.room_group_name = f"chat_{self.thread_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Get current message count so we continue the sequence correctly
            self.message_count = await self.get_message_count()
            logger.info(f"WS connected: thread={self.thread_id}, message_count={self.message_count}")

            # Pick greeting based on whether we know the user
            greeting = await self._pick_greeting()
            await self.send(text_data=json.dumps({
                'message': greeting,
                'sender': 'hari',
            }))

        except Exception as e:
            logger.error(f"WS connect error: {e}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.session_messages:
                conversation_count = await self.save_chat_memory()

                if self.user_id:
                    # Determine whether this session hits the Hari-update milestone
                    update_hari = bool(
                        conversation_count and
                        conversation_count % PERSONA_UPDATE_INTERVAL == 0
                    )
                    # Await the extraction pipeline directly — fire-and-forget
                    # via create_task can get GC'd before completion on Daphne
                    from .memory_extractor import run_extraction_pipeline
                    try:
                        await run_extraction_pipeline(
                            user_id=self.user_id,
                            session_messages=list(self.session_messages),
                            update_hari=update_hari,
                        )
                    except Exception as e:
                        logger.error(f"Extraction pipeline failed: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"WS disconnect error: {e}", exc_info=True)
        finally:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        import asyncio
        user_message = ''
        ai_response = "아 미안 나 지금 좀 상태가 안 좋아... 잠만 기다려줘"
        try:
            data = json.loads(text_data)
            user_message = data.get('message', '')
            if not user_message:
                return

            # Save user message (non-critical — don't let a DB failure block the reply)
            try:
                await self.save_message(sender_type=True, content=user_message)
            except Exception as e:
                logger.error(f"Failed to save user message: {e}", exc_info=True)

            # Get AI response
            from .engine import engine
            try:
                loop = asyncio.get_running_loop()
                ai_response = await asyncio.wait_for(
                    loop.run_in_executor(None, engine.get_response, user_message, self.thread_id),
                    timeout=60.0
                )
            except asyncio.TimeoutError:
                logger.error(f"AI engine timed out for thread {self.thread_id}")
                ai_response = "아 미안 나 잠깐 딴 생각 했어ㅋㅋ 다시 말해줘"
            except Exception as e:
                logger.error(f"AI engine error: {e}", exc_info=True)
                ai_response = "아 미안 나 지금 좀 상태가 안 좋아... 잠만 기다려줘"

        except Exception as e:
            logger.error(f"WS receive error: {e}", exc_info=True)

        finally:
            # Always send a reply so the client never hangs
            try:
                await self.send(text_data=json.dumps({
                    'message': ai_response,
                    'sender': 'hari',
                }))
            except Exception as e:
                logger.error(f"Failed to send WS response: {e}", exc_info=True)
                return

            # Save Hari's response after sending (non-critical)
            if user_message:
                try:
                    await self.save_message(sender_type=False, content=ai_response)
                except Exception as e:
                    logger.error(f"Failed to save Hari response: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    #  Greeting logic                                                    #
    # ------------------------------------------------------------------ #

    async def _pick_greeting(self) -> str:
        """Choose a greeting based on whether this is a new or returning user."""
        is_new = self.message_count == 0
        if is_new:
            return _FIRST_GREETING

        name = await self._get_user_name()
        if name:
            return random.choice(_RETURNING_GREETINGS).format(name=name)
        return random.choice(_RETURNING_NO_NAME_GREETINGS)

    @database_sync_to_async
    def _get_user_name(self):
        """Look up the user's name/nickname from user_persona."""
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT trait_value FROM user_persona
                WHERE user_id = %s
                  AND trait_key IN ('name', 'nickname', 'real_name')
                  AND is_active = TRUE
                ORDER BY importance DESC
                LIMIT 1
                """,
                [self.user_id],
            )
            row = cur.fetchone()
            return row[0] if row else None

    # ------------------------------------------------------------------ #
    #  DB helpers (run in thread pool via database_sync_to_async)         #
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def get_message_count(self):
        """Return the number of messages already saved for this user/session."""
        if self.user_id:
            return Message.objects.filter(user_id=self.user_id).count()
        if self.anonymous_id:
            return Message.objects.filter(anonymous_id=self.anonymous_id).count()
        return 0

    @database_sync_to_async
    def save_message(self, sender_type, content):
        self.message_count += 1
        # Track in session first — even if the DB write fails the memory summary still works
        self.session_messages.append({
            'sender': 'user' if sender_type else 'hari',
            'content': content,
        })
        Message.objects.create(
            user_id=self.user_id,
            sender_type=sender_type,
            content=content,
            count=self.message_count,
            anonymous_id=self.anonymous_id,
        )

    @database_sync_to_async
    def save_chat_memory(self):
        """
        Persist a summary of this conversation session to chat_memory.
        Returns the total number of conversations this user has had.
        """
        # Build conversation transcript
        lines = [
            f"{'User' if m['sender'] == 'user' else 'Hari'}: {m['content']}"
            for m in self.session_messages
        ]
        transcript = "\n".join(lines)

        # Summarize transcript via LLM (fall back to raw transcript on failure)
        summary = transcript
        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatOpenAI(model="gpt-5.4-mini", temperature=1, timeout=15)
            result = llm.invoke([
                SystemMessage(content=(
                    "You are a concise conversation summarizer. "
                    "Summarize the following conversation in 2-4 sentences in Korean. "
                    "Focus on: key topics discussed, any personal information shared, "
                    "important decisions or preferences expressed. "
                    "Do NOT include greetings or filler. Write in plain descriptive style."
                )),
                HumanMessage(content=transcript),
            ])
            if result.content.strip():
                summary = result.content.strip()
                logger.info("Conversation summarized successfully (%d chars → %d chars)", len(transcript), len(summary))
        except Exception as e:
            logger.error(f"Conversation summarization failed, using raw transcript: {e}", exc_info=True)

        record = ChatMemory.objects.create(
            user_id=self.user_id,
            anonymous_id=self.anonymous_id,
            summary=summary,
            ended_at=timezone.now(),
        )

        # Generate and store summary embedding (non-critical)
        try:
            from .memory_vector import embed_text, save_summary_vector
            vector = embed_text(summary)
            if vector:
                save_summary_vector(record.memory_id, vector)
        except Exception as e:
            logger.error(f"Failed to save summary vector for memory {record.memory_id}: {e}", exc_info=True)

        if self.user_id:
            return ChatMemory.objects.filter(user_id=self.user_id).count()
        return None

    # trigger_persona_update is now handled inside disconnect() via
    # run_extraction_pipeline(update_hari=True) at the PERSONA_UPDATE_INTERVAL milestone.
