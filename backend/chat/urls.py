from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatSessionViewSet, MessageViewSet, chat_index

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='chatsession')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', chat_index, name='chat_index'),
    path('api/', include(router.urls)),
]
