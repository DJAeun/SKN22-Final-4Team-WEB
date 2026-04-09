import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .models import RpgSession
from .engine import MainEngine, apply_status_metadata_to_session, extract_status_metadata, strip_status_content
from .korean_text import render_user_template

class RoleplayConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Allow connection if user is authenticated and session is valid
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        
        # Verify Session
        session = await self._get_session(self.session_id)
        if not session:
            await self.close()
            return
            
        is_owner = await self._verify_user(session, self.scope["user"])
        if self.scope["user"].is_authenticated and not is_owner:
            await self.close()
            return
            
        self.room_group_name = f'roleplay_{self.session_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        
        # Send first message if chat is empty
        await self._send_first_message_if_needed(session)

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        user_message = text_data_json['message']

        # Notify UI we received
        await self.send(text_data=json.dumps({
            'type': 'status',
            'message': 'processing'
        }))

        # Delegate LLM generation to background or synchronous blocking call
        # Since this runs in an async loop, sync DB/LLM calls must be wrapped in sync_to_async
        engine_response = await self._generate_engine_response(self.session_id, user_message)

        # Send response back to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': engine_response['content'],
            'status_snapshot': engine_response.get('status_snapshot', {}),
        }))

    @sync_to_async
    def _needs_first_message(self, session):
        from .models import RpgChatLog
        return not RpgChatLog.objects.filter(session=session).exists()

    @sync_to_async
    def _create_and_get_first_message(self, session):
        from .models import RpgLorebook, RpgChatLog
        first_ms_lore = RpgLorebook.objects.filter(keywords='{FirstMessage}').first()
        content = "안녕!"
        if first_ms_lore:
            content = first_ms_lore.lorebook
        
        content = render_user_template(content, session.user_nickname)
        status_snapshot = extract_status_metadata(content)
        visible_content = strip_status_content(content)
        apply_status_metadata_to_session(session, status_snapshot)

        new_log = RpgChatLog.objects.create(
            session=session,
            role="NPC Engine",
            raw_content=content,
            content=visible_content,
            status_snapshot={
                'date': status_snapshot.get('date', ''),
                'time': status_snapshot.get('time', ''),
                'location': status_snapshot.get('location', ''),
                'stress': status_snapshot.get('stress'),
                'crack_stage': status_snapshot.get('crack_stage'),
                'thought': status_snapshot.get('thought', ''),
            },
            token_count=len(content) // 4
        )
        return {
            'content': visible_content,
            'status_snapshot': new_log.status_snapshot,
        }

    async def _send_first_message_if_needed(self, session):
        needs_msg = await self._needs_first_message(session)
        if needs_msg:
            first_message = await self._create_and_get_first_message(session)
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': first_message['content'],
                'status_snapshot': first_message.get('status_snapshot', {}),
            }))

    @sync_to_async
    def _verify_user(self, session, scope_user):
        return session.user_id == scope_user.id

    @sync_to_async
    def _get_session(self, session_id):
        try:
            return RpgSession.objects.get(id=session_id)
        except RpgSession.DoesNotExist:
            return None

    @sync_to_async
    def _generate_engine_response(self, session_id, message):
        session = RpgSession.objects.get(id=session_id)
        engine = MainEngine(session)
        return engine.generate_response(message)
