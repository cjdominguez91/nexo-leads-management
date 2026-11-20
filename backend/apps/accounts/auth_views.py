from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .google_auth import verify_google_id_token
from .models import AuthProvider, User
from .serializers import UserSerializer


def _token_response(user):
    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }
    )


class AuthConfigView(APIView):
    """Endpoint público: el frontend lo consulta para decidir qué botón de
    login mostrar, en vez de tener el switch hardcodeado en el build."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "google_enabled": settings.AUTH_GOOGLE_ENABLED,
                "local_enabled": settings.AUTH_LOCAL_ENABLED,
                "google_client_id": settings.GOOGLE_OAUTH_CLIENT_ID if settings.AUTH_GOOGLE_ENABLED else "",
            }
        )


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not settings.AUTH_GOOGLE_ENABLED:
            return Response({"detail": "Login con Google deshabilitado."}, status=status.HTTP_403_FORBIDDEN)

        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        profile = verify_google_id_token(token)

        user, created = User.objects.get_or_create(
            email=profile.email,
            defaults={
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "avatar_url": profile.picture,
                "auth_provider": AuthProvider.GOOGLE,
                "is_active": False,  # requiere activación + asignación de rol por un ADMIN
            },
        )

        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            return Response(
                {"detail": "Cuenta creada. Está pendiente de activación por un administrador."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user.is_active:
            return Response({"detail": "Tu cuenta está inactiva o pendiente de activación."}, status=status.HTTP_403_FORBIDDEN)

        update_fields = []
        if user.auth_provider != AuthProvider.GOOGLE:
            user.auth_provider = AuthProvider.GOOGLE
            update_fields.append("auth_provider")
        if profile.picture and user.avatar_url != profile.picture:
            user.avatar_url = profile.picture
            update_fields.append("avatar_url")
        if update_fields:
            user.save(update_fields=update_fields)

        return _token_response(user)


class LocalLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not settings.AUTH_LOCAL_ENABLED:
            return Response({"detail": "Login local deshabilitado."}, status=status.HTTP_403_FORBIDDEN)

        email = request.data.get("email")
        password = request.data.get("password")
        if not email or not password:
            return Response({"detail": "email y password son requeridos."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, username=email, password=password)
        if user is None:
            return Response({"detail": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "Tu cuenta está inactiva."}, status=status.HTTP_403_FORBIDDEN)

        return _token_response(user)
