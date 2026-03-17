import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatSession, Message
import logging

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = None
        try:
            self.user = self.scope["user"]
            session = self.scope.get("session")
            session_key = session.session_key if session else None
            
            # Get session_id from URL if present
            url_route = self.scope.get('url_route', {})
            session_id = url_route.get('kwargs', {}).get('session_id')

            logger.debug(f"WS connecting: user={self.user}, session_key={session_key}, session_id={session_id}")

            # Get session from DB
            self.session = await self.get_or_create_session(self.user, session_key, session_id)
            
            if self.session:
                # Group by session ID to allow multiple sessions per user
                self.room_group_name = f"chat_{self.session.id}"
            else:
                # Fallback group for users without a valid session
                self.room_group_name = f"chat_anon_{id(self)}"
                logger.debug(f"No session found, using fallback group: {self.room_group_name}")
                
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            logger.info(f"WS accepted for group {self.room_group_name}")

        except Exception as e:
            logger.error(f"WS connect error: {e}", exc_info=True)
            if hasattr(self, 'room_group_name') and self.room_group_name:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await self.close()

    @database_sync_to_async
    def get_or_create_session(self, user, session_key, session_id=None):
        try:
            if session_id:
                # If specific session requested, find it and verify ownership
                if user.is_authenticated:
                    return ChatSession.objects.filter(id=session_id, user=user).first()
                else:
                    return ChatSession.objects.filter(id=session_id, user=None, summary=session_key).first()

            if user.is_authenticated:
                session = ChatSession.objects.filter(user=user).order_by('-updated_at').first()
                if not session:
                    session = ChatSession.objects.create(user=user)
            else:
                if not session_key:
                    logger.debug("No session_key for anonymous user in get_or_create_session")
                    return None
                # session_key is stored in summary for guests
                session = ChatSession.objects.filter(user=None, summary=session_key).order_by('-updated_at').first()
                if not session:
                    logger.debug(f"Creating new guest session for key: {session_key}")
                    session = ChatSession.objects.create(user=None, summary=session_key)
            return session
        except Exception as e:
            logger.error(f"get_or_create_session error: {e}", exc_info=True)
            raise e

    @database_sync_to_async
    def save_message(self, session, sender, text):
        if session:
            return Message.objects.create(session=session, sender=sender, text=text)
        return None

    async def disconnect(self, close_code):
        # Leave room group
        if self.room_group_name:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json.get('message', '')

            if not message:
                return

            if self.session:
                await self.save_message(self.session, 'user', message)

            from .engine import engine
            import asyncio
            
            try:
                loop = asyncio.get_event_loop()
                ai_response = await loop.run_in_executor(None, engine.get_response, message)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"WebSocket consumer AI error: {e}")
                ai_response = "앗, 미안해! 지금 목소리가 잘 안 나와... 잠시 후에 다시 말해줄래? 😢"

            if self.session:
                await self.save_message(self.session, 'hari', ai_response)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': ai_response,
                    'sender': 'hari'
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"WebSocket receive error: {e}")

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender = event.get('sender', 'system')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender
        }))
