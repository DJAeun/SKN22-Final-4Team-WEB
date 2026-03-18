import json
import uuid
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
            self.user = self.scope["user"]
            self.session_messages = []  # messages recorded in this connection

            # Use user ID as LangGraph thread (persistent memory across sessions)
            if self.user.is_authenticated:
                self.thread_id = str(self.user.id)
                self.anonymous_id = None
            else:
                django_session = self.scope.get("session")
                if django_session and not django_session.session_key:
                    # Ensure a session key exists so anonymous users get a stable ID
                    await django_session.asave()
                self.anonymous_id = (
                    django_session.session_key if django_session else str(uuid.uuid4())
                )
                self.thread_id = f"anon_{self.anonymous_id}"

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
        try:
            data = json.loads(text_data)
            user_message = data.get('message', '')
            if not user_message:
                return

            # Save user message
            await self.save_message(sender_type=True, content=user_message)

            # Get AI response
            from .engine import engine
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                ai_response = await loop.run_in_executor(
                    None, engine.get_response, user_message, self.thread_id
                )
            except Exception as e:
                logger.error(f"AI engine error: {e}", exc_info=True)
                ai_response = "앗, 미안해! 지금 목소리가 잘 안 나와... 잠시 후에 다시 말해줄래? 😢"

            # Save Hari's response
            await self.save_message(sender_type=False, content=ai_response)

            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat_message', 'message': ai_response, 'sender': 'hari'}
            )

        except Exception as e:
            logger.error(f"WS receive error: {e}", exc_info=True)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event.get('sender', 'system'),
        }))

    # ------------------------------------------------------------------ #
    #  DB helpers (run in thread pool via database_sync_to_async)         #
    # ------------------------------------------------------------------ #

    @database_sync_to_async
    def get_message_count(self):
        """Return the number of messages already saved for this user/session."""
        if self.user.is_authenticated:
            return Message.objects.filter(user=self.user).count()
        if self.anonymous_id:
            return Message.objects.filter(anonymous_id=self.anonymous_id).count()
        return 0

    @database_sync_to_async
    def save_message(self, sender_type, content):
        self.message_count += 1
        user = self.user if self.user.is_authenticated else None
        Message.objects.create(
            user=user,
            sender_type=sender_type,
            content=content,
            count=self.message_count,
            anonymous_id=self.anonymous_id,
        )
        self.session_messages.append({
            'sender': 'user' if sender_type else 'hari',
            'content': content,
        })

    @database_sync_to_async
    def save_chat_memory(self):
        """
        Persist a summary of this conversation session to chat_memory.
        Returns the total number of conversations this user has had.
        """
        user = self.user if self.user.is_authenticated else None

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
            user=user,
            anonymous_id=self.anonymous_id,
            summary=summary,
            keywords=keywords,
            ended_at=timezone.now(),
        )

        if user:
            return ChatMemory.objects.filter(user=user).count()
        return None

    @database_sync_to_async
    def trigger_persona_update(self):
        """
        Called every PERSONA_UPDATE_INTERVAL conversations.
        Fetch recent chat_memory rows and update user_persona / hari_knowledge via GPT.

        TODO: implement GPT batch enrichment here.
        Example flow:
            1. Load last N ChatMemory summaries for this user
            2. Call OpenAI to extract persona traits / keywords
            3. Upsert rows in user_persona table
            4. Optionally update hari_knowledge based on recurring themes
        """
        user = self.user if self.user.is_authenticated else None
        if not user:
            return

        logger.info(
            f"[PersonaUpdate] Triggered for user={user.id} "
            f"at {PERSONA_UPDATE_INTERVAL}-conversation milestone"
        )
        # ── Insert GPT enrichment logic here ──────────────────────────────
