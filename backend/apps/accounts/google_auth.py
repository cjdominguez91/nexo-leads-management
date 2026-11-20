"""Verificación server-side de ID tokens de Google Identity Services.

No se usa la API de Admin Directory (requiere ser super-admin del Workspace,
inviable para un desarrollo personal). Solo se validan los claims estándar
del token OIDC que Google entrega a cualquier cuenta: email, name, picture.
"""

from dataclasses import dataclass

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework.exceptions import AuthenticationFailed


@dataclass
class GoogleProfile:
    email: str
    first_name: str
    last_name: str
    picture: str


def verify_google_id_token(token: str) -> GoogleProfile:
    try:
        claims = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
        )
    except ValueError as exc:
        raise AuthenticationFailed("Token de Google inválido o expirado.") from exc

    if not claims.get("email_verified", False):
        raise AuthenticationFailed("El correo de Google no está verificado.")

    domain = settings.GOOGLE_WORKSPACE_DOMAIN
    if domain and claims.get("hd") != domain:
        raise AuthenticationFailed(f"Solo se permite el dominio {domain}.")

    full_name = claims.get("name", "")
    given_name, _, family_name = full_name.partition(" ")

    return GoogleProfile(
        email=claims["email"],
        first_name=claims.get("given_name", given_name),
        last_name=claims.get("family_name", family_name),
        picture=claims.get("picture", ""),
    )
