import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message, ChatMemory

logger = logging.getLogger(__name__)

# Trigger persona enrichment every N completed conversations per user
PERSONA_UPDATE_INTERVAL = 100


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

            # Send welcome message
            await self.send(text_data=json.dumps({
                'message': '안녕하세요! 저는 강하리예요 😊 오늘은 어떤 이야기 나눠볼까요?',
                'sender': 'hari',
            }))

        except Exception as e:
            logger.error(f"WS connect error: {e}", exc_info=True)
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.session_messages:
                conversation_count = await self.save_chat_memory()

                # Every PERSONA_UPDATE_INTERVAL conversations, trigger persona enrichment
                if conversation_count and conversation_count % PERSONA_UPDATE_INTERVAL == 0:
                    await self.trigger_persona_update()
        except Exception as e:
            logger.error(f"WS disconnect error: {e}", exc_info=True)
        finally:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        import asyncio
        user_message = ''
        ai_response = "앗, 미안해! 지금 목소리가 잘 안 나와... 잠시 후에 다시 말해줄래? 😢"
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
                ai_response = "앗, 미안해! 하리가 잠깐 딴 생각 했나봐... 다시 말해줄래? 😅"
            except Exception as e:
                logger.error(f"AI engine error: {e}", exc_info=True)
                ai_response = "앗, 미안해! 지금 목소리가 잘 안 나와... 잠시 후에 다시 말해줄래? 😢"

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
        summary = "\n".join(lines)

        # Simple keyword extraction from user messages (words longer than 3 chars)
        user_text = " ".join(
            m['content'] for m in self.session_messages if m['sender'] == 'user'
        )
        words = {w.strip('.,!?').lower() for w in user_text.split() if len(w) > 3}
        keywords = ", ".join(list(words)[:20])

        ChatMemory.objects.create(
            user_id=self.user_id,
            anonymous_id=self.anonymous_id,
            summary=summary,
            keywords=keywords,
            ended_at=timezone.now(),
        )

        if self.user_id:
            return ChatMemory.objects.filter(user_id=self.user_id).count()
        return None

    @database_sync_to_async
    def trigger_persona_update(self):
        if not self.user_id:
            return
        logger.info(
            f"[PersonaUpdate] Triggered for user={self.user_id} "
            f"at {PERSONA_UPDATE_INTERVAL}-conversation milestone"
        )
        # ── Insert GPT enrichment logic here ──────────────────────────────
