import json

from channels.generic.websocket import AsyncWebsocketConsumer


class NotificationConsumer(AsyncWebsocketConsumer):
    """Un grupo por usuario (`user_<id>`) — alcanza para notificaciones
    personales; no hay concepto de "sala" compartida en Fase 4a."""

    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return
        self.group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # Nombre del método = valor de "type" en channel_layer.group_send(...)
    # (con guiones bajos en vez de puntos — Channels lo exige así).
    async def notify_event(self, event):
        await self.send(text_data=json.dumps(event["data"]))
