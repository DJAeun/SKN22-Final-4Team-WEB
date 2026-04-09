from rest_framework import serializers
from .models import RpgSession, RpgChatLog
from .engine import build_status_snapshot, extract_status_metadata, normalize_meta_text

class RpgSessionSerializer(serializers.ModelSerializer):
    current_thought = serializers.SerializerMethodField()
    current_date = serializers.SerializerMethodField()
    current_time = serializers.SerializerMethodField()
    current_location = serializers.SerializerMethodField()

    class Meta:
        model = RpgSession
        fields = ['id', 'user', 'user_nickname', 'total_tokens', 'status_window_enabled', 'stress', 'crack_stage', 'current_thought', 'current_date', 'current_time', 'current_location', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'total_tokens', 'stress', 'crack_stage', 'current_thought', 'current_date', 'current_time', 'current_location', 'created_at', 'updated_at']

    def _get_latest_status_metadata(self, obj):
        cached = getattr(obj, '_cached_latest_status_metadata', None)
        if cached is not None:
            return cached

        latest_engine_log = (
            RpgChatLog.objects.filter(session=obj, role='NPC Engine')
            .exclude(raw_content__isnull=True)
            .exclude(raw_content__exact='')
            .order_by('-id')
            .first()
        )
        if not latest_engine_log:
            obj._cached_latest_status_metadata = {}
            return obj._cached_latest_status_metadata

        if latest_engine_log.status_snapshot:
            obj._cached_latest_status_metadata = latest_engine_log.status_snapshot
            return obj._cached_latest_status_metadata

        obj._cached_latest_status_metadata = build_status_snapshot(extract_status_metadata(latest_engine_log.raw_content))
        return obj._cached_latest_status_metadata

    def get_current_thought(self, obj):
        return normalize_meta_text(self._get_latest_status_metadata(obj).get('thought', ''))

    def get_current_date(self, obj):
        return normalize_meta_text(self._get_latest_status_metadata(obj).get('date', ''))

    def get_current_time(self, obj):
        return normalize_meta_text(self._get_latest_status_metadata(obj).get('time', ''))

    def get_current_location(self, obj):
        return normalize_meta_text(self._get_latest_status_metadata(obj).get('location', ''))

class RpgChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RpgChatLog
        fields = ['id', 'session', 'role', 'content', 'status_snapshot', 'image_command', 'image_url', 'created_at']
        read_only_fields = ['id', 'session', 'role', 'content', 'status_snapshot', 'image_command', 'image_url', 'created_at']
