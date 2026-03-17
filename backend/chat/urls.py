from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatSessionViewSet, MessageViewSet, chat_index, debug_env

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='chatsession')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', chat_index, name='chat_index'),
    path('debug-env/', debug_env, name='debug_env'),
    path('api/', include(router.urls)),
]
