import asyncio
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import connection
from django.utils import timezone
from .models import Message, ChatMemory

logger = logging.getLogger(__name__)

# Trigger Hari persona enrichment every N completed conversations per user
PERSONA_UPDATE_INTERVAL = 20



class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            from django.conf import settings
            user = self.scope["user"]

            if not user.is_authenticated:
                if not settings.DEBUG:
                    await self.close(code=4401)
                    return
                # 로컬 개발 전용 guest 모드
                self.user_id = None
                self.thread_id = 'guest'
                self.message_count = 0
            else:
                self.user_id = user.id
                self.message_count = 0

            self.session_messages = []
            import uuid
            url_session = self.scope['url_route']['kwargs'].get('session_id')
            self.session_id = str(url_session) if url_session else str(uuid.uuid4())

            # When a URL session_id is provided (e.g. eval scripts), use it as
            # the LangGraph thread so each session gets an isolated checkpoint.
            # Regular users connect at /ws/chat/ (no session_id), keeping the
            # existing per-user thread behaviour.
            if url_session and self.user_id is not None:
                self.thread_id = str(url_session)
            elif self.user_id is not None:
                self.thread_id = str(self.user_id)
            else:
                self.thread_id = 'guest'

            self.room_group_name = f"chat_{self.thread_id}"
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # DB에서 메시지 수 조회 (guest 모드거나 DB 없으면 0 유지)
            if self.user_id is not None:
                try:
                    self.message_count = await self.get_message_count()
                except Exception:
                    self.message_count = 0

            logger.info(f"WS connected: thread={self.thread_id}, message_count={self.message_count}")

            # First-time user: Hari opens the conversation herself. The opening
            # is LLM-generated and seeded into the LangGraph checkpoint so the
            # model has full context when the user replies (prevents the "민제"
            # regression where a hardcoded greeting wasn't in the LLM's history).
            if (
                self.user_id is not None
                and self.message_count == 0
                and await self._needs_opening()
            ):
                try:
                    from .engine import engine
                    loop = asyncio.get_running_loop()
                    opening = await asyncio.wait_for(
                        loop.run_in_executor(
                            None, engine.generate_opening, self.user_id, self.thread_id
                        ),
                        timeout=15.0,
                    )
                    if opening:
                        await self.save_message(sender_type=False, content=opening)
                        await self.send(text_data=json.dumps({
                            'message': opening,
                            'sender': 'hari',
                        }))
                except Exception as e:
                    logger.error(f"Opening generation failed: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"WS connect error: {e}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if getattr(self, 'session_messages', None):
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

        # Ignore pings and messages with no text — return before the
        # try/finally block so we don't accidentally send the fallback.
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return
        if data.get('ping') or not data.get('message', '').strip():
            return

        user_message = data['message'].strip()

        # save_only: just persist individual message to DB, no AI response
        if data.get('save_only'):
            try:
                await self.save_message(sender_type=True, content=user_message)
            except Exception as e:
                logger.error(f"Failed to save user message: {e}", exc_info=True)
            return

        skip_save = data.get('skip_save', False)

        ai_response = "아 미안 나 지금 좀 상태가 안 좋아... 잠만 기다려줘"
        try:

            # Save user message (skip if individual messages were already saved)
            if not skip_save:
                try:
                    await self.save_message(sender_type=True, content=user_message)
                except Exception as e:
                    logger.error(f"Failed to save user message: {e}", exc_info=True)

            # Get AI response
            from .engine import engine
            used_web_search = False
            try:
                loop = asyncio.get_running_loop()
                ai_response, used_web_search = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, engine.get_response, user_message, self.thread_id, self.user_id
                    ),
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
                    await self.save_message(sender_type=False, content=ai_response, used_web_search=used_web_search)
                except Exception as e:
                    logger.error(f"Failed to save Hari response: {e}", exc_info=True)

    # ------------------------------------------------------------------ #
    #  DB helpers (run in thread pool via database_sync_to_async)         #
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def get_message_count(self):
        """Return the number of messages already saved for this user."""
        return Message.objects.filter(user_id=self.user_id).count()

    @database_sync_to_async
    def _needs_opening(self):
        """
        True only when:
          • the user has no identity/name persona row (first-time user), AND
          • no Hari message exists for this user yet (guards against re-entry
            after a disconnect that already generated an opening).
        """
        from .models import UserPersona
        has_name = UserPersona.objects.filter(
            user_id=self.user_id,
            category='identity',
            trait_key='name',
            is_active=True,
        ).exists()
        if has_name:
            return False
        has_hari_msg = Message.objects.filter(
            user_id=self.user_id,
            sender_type=False,
        ).exists()
        return not has_hari_msg

    @database_sync_to_async
    def save_message(self, sender_type, content, used_web_search=False):
        self.message_count += 1
        self.session_messages.append({
            'sender': 'user' if sender_type else 'hari',
            'content': content,
        })
        if self.user_id is None:
            return  # guest 모드 — DB 저장 skip
        Message.objects.create(
            user_id=self.user_id,
            sender_type=sender_type,
            content=content,
            count=self.message_count,
            session_id=self.session_id,
            used_web_search=used_web_search,
        )

    @database_sync_to_async
    def save_chat_memory(self):
        """
        Persist a summary of this conversation session to chat_memory.
        Returns the total number of conversations this user has had.
        """
        if self.user_id is None:
            return 0  # guest 모드 — DB 저장 skip

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
            session_id=self.session_id,
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

        return ChatMemory.objects.filter(user_id=self.user_id).count()

    # trigger_persona_update is now handled inside disconnect() via
    # run_extraction_pipeline(update_hari=True) at the PERSONA_UPDATE_INTERVAL milestone.
