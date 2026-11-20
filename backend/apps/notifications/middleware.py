"""Autenticación para WebSockets vía JWT.

El `AuthMiddlewareStack` que trae Channels de fábrica autentica por sesión
(cookie) — este proyecto usa JWT para todo (SimpleJWT), no hay sesión de
Django activa en el SPA, así que ese middleware siempre vería
AnonymousUser. El navegador tampoco permite mandar headers custom en la
conexión WebSocket nativa, así que el token viaja como query param
(`?token=...`), igual que hacen la mayoría de implementaciones JWT+WS.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(token: str):
    from apps.accounts.models import User

    try:
        validated = AccessToken(token)
        return User.objects.get(pk=validated["user_id"], is_active=True)
    except (TokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get("query_string", b"").decode()
        token = parse_qs(query_string).get("token", [None])[0]
        scope["user"] = await _get_user(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
