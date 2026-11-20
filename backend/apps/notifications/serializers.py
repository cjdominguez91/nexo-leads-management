from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "tipo", "payload", "leido", "created_at"]
        read_only_fields = fields
