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
from chat.views import health_check, homepage, mypage, frontend_chat, abouthari_page, gallery_page, news_page, video_page, membership_page, contact_form, frontend_signup_view, admin_stats_api, youtube_stats_api, youtube_oauth_start, youtube_oauth_callback, youtube_analytics_api, youtube_video_analytics_api, instagram_stats_api, instagram_media_api, instagram_token_api, tiktok_oauth_start, tiktok_oauth_callback, tiktok_stats_api


def robots_txt(_request):
    return HttpResponse('User-agent: *\nAllow: /\n', content_type='text/plain')

def tiktok_verify(_request):
    return HttpResponse('tiktok-developers-site-verification=hUjyVzNan045mImBqBP0HionITouB7wa', content_type='text/plain')


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
    path('admin/youtube-stats/', youtube_stats_api, name='youtube_stats_api'),
    path('admin/youtube-oauth-start/', youtube_oauth_start, name='youtube_oauth_start'),
    path('admin/youtube-oauth-callback/', youtube_oauth_callback, name='youtube_oauth_callback'),
    path('admin/youtube-analytics/', youtube_analytics_api, name='youtube_analytics_api'),
    path('admin/youtube-video-analytics/', youtube_video_analytics_api, name='youtube_video_analytics_api'),
    path('admin/instagram-stats/', instagram_stats_api, name='instagram_stats_api'),
    path('admin/instagram-media/', instagram_media_api, name='instagram_media_api'),
    path('admin/instagram-token/', instagram_token_api, name='instagram_token_api'),
    path('admin/tiktok-oauth-start/', tiktok_oauth_start, name='tiktok_oauth_start'),
    path('admin/tiktok-oauth-callback/', tiktok_oauth_callback, name='tiktok_oauth_callback'),
    path('admin/tiktok-stats/', tiktok_stats_api, name='tiktok_stats_api'),
    path('tiktokhUjyVzNan045mImBqBP0HionITouB7wa.txt', tiktok_verify),
    path('admin/tiktok-oauth-callback/tiktokhUjyVzNan045mImBqBP0HionITouB7wa.txt', tiktok_verify),
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
