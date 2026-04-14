"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.views.static import serve
from django.http import HttpResponse
from chat.views import health_check, homepage, mypage, frontend_chat, abouthari_page, gallery_page, news_page, video_page, membership_page, contact_form, frontend_signup_view, admin_stats_api


def robots_txt(_request):
    return HttpResponse('User-agent: *\nAllow: /\n', content_type='text/plain')

def google_verify(_request):
    return HttpResponse('google-site-verification: google840fb0dac52a59f6.html', content_type='text/html')

urlpatterns = [
    path('', homepage, name='home'),
    path('homepage/', homepage, name='homepage'),
    path('mypage/', mypage, name='mypage'),
    path('abouthari/', abouthari_page, name='abouthari'),
    path('gallery/', gallery_page, name='gallery'),
    path('news/', news_page, name='news'),
    path('video/', video_page, name='video'),
    path('membership/', membership_page, name='membership'),
    path('contact/', contact_form, name='contact_form'),
    path('hari-chat/', frontend_chat, name='frontend_chat'),
    path('health/', health_check, name='health_check'),
    path('roleplay/', include('roleplay.page_urls')),
    path('admin/dashboard-stats/', admin_stats_api, name='admin_stats_api'),
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/images/hari_favicon.png', permanent=True)),
    path('robots.txt', robots_txt),
    path('google840fb0dac52a59f6.html', google_verify),
    path('accounts/', include('allauth.urls')),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', frontend_signup_view, name='frontend_registration'),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    path('api/chat/', include('chat.urls')),
    path('api/roleplay/', include('roleplay.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Docker Compose-based EB doesn't provide the host Nginx proxy config,
    # so Django serves committed media assets directly in production.
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
