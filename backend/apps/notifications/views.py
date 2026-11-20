from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Cada usuario ve solo las suyas — no hay scope territorial que
    aplicar acá, la pertenencia ya es 1 a 1 por usuario."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["leido", "tipo"]

    def get_queryset(self):
        return Notification.objects.filter(usuario=self.request.user)

    @action(detail=True, methods=["post"], url_path="marcar-leida")
    def marcar_leida(self, request, pk=None):
        notification = self.get_object()
        if not notification.leido:
            notification.leido = True
            notification.save(update_fields=["leido"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="marcar-todas-leidas")
    def marcar_todas_leidas(self, request):
        self.get_queryset().filter(leido=False).update(leido=True)
        return Response({"detail": "ok"})
