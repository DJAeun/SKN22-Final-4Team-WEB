from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleplaySessionViewSet, roleplay_test

router = DefaultRouter()
router.register(r'sessions', RoleplaySessionViewSet, basename='roleplay-session')

urlpatterns = [
    path('test/', roleplay_test, name='roleplay-test'),
    path('', include(router.urls)),
]
