from django.urls import path
from .views import roleplay_page

urlpatterns = [
    path('', roleplay_page, name='roleplay'),
]
