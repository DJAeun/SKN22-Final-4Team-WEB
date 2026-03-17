from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatSessionViewSet, MessageViewSet, chat_index, debug_env,
    login_view, signup_view, logout_view, signup_success
)

router = DefaultRouter()
router.register(r'sessions', ChatSessionViewSet, basename='chatsession')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', chat_index, name='chat_index'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('signup/success/', signup_success, name='signup_success'),
    path('logout/', logout_view, name='logout'),
    path('debug-env/', debug_env, name='debug_env'),
    path('api/', include(router.urls)),
]
