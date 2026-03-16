import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = 'user_chat'
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', '')

        if not message:
            return

        from .engine import engine
        import asyncio
        
        # Call the AI Engine asynchronously
        loop = asyncio.get_event_loop()
        ai_response = await loop.run_in_executor(None, engine.get_response, message)

        # 3. Send AI response to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': ai_response,
                'sender': 'hari'
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        sender = event.get('sender', 'system')

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender
        }))
