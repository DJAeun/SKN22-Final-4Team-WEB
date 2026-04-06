from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

@login_required
def roleplay_test(request):
    return render(request, 'roleplay/test.html')

@login_required
def roleplay_page(request):
    return render(request, 'roleplay/roleplay.html')
from .models import RpgSession, RpgChatLog
from .serializers import RpgSessionSerializer, RpgChatLogSerializer

class RoleplaySessionViewSet(viewsets.ModelViewSet):
    serializer_class = RpgSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RpgSession.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        session = self.get_object()
        logs = RpgChatLog.objects.filter(session=session).order_by('created_at')
        serializer = RpgChatLogSerializer(logs, many=True)
        return Response(serializer.data)
