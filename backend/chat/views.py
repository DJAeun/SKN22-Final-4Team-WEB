from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.response import Response
from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from .models import Message, ChatMemory, HariKnowledge, GeneratedContent, VisitLog, UserPersona
from .serializers import MessageSerializer, ChatMemorySerializer, UserNameSerializer


def _try_jwt_auth(request):
    """세션 인증이 없을 때 JWT 쿠키로 request.user를 설정한다."""
    if request.user.is_authenticated:
        return
    try:
        result = JWTCookieAuthentication().authenticate(request)
        if result:
            request.user = result[0]
    except Exception:
        pass


@ensure_csrf_cookie
def homepage(request):
    _try_jwt_auth(request)
    return render(request, 'frontend/homepage.html')


def mypage(request):
    return render(request, 'frontend/mypage.html')


def abouthari_page(request):
    _try_jwt_auth(request)
    return render(request, 'frontend/abouthari.html')


def gallery_page(request):
    return render(request, 'frontend/gallery.html')


def news_page(request):
    return render(request, 'frontend/news.html')


@ensure_csrf_cookie
def video_page(request):
    return render(request, 'frontend/video.html')


def frontend_chat(request):
    if not settings.DEBUG:
        _try_jwt_auth(request)
        if not request.user.is_authenticated:
            return redirect('home')
    return render(request, 'frontend/chat.html')


def membership_page(request):
    return render(request, 'frontend/membership.html')


def chat_index(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'chat/index.html')


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Message.objects.filter(user=self.request.user).order_by('created_at')


class ChatMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatMemorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatMemory.objects.filter(user=self.request.user).order_by('-ended_at')


@api_view(['GET', 'POST'])
@perm_classes([permissions.IsAuthenticated])
def user_name_view(request):
    """GET: return user's name or null.  POST: save/update name."""
    user = request.user

    if request.method == 'GET':
        persona = UserPersona.objects.filter(
            user=user,
            category='identity',
            trait_key='name',
            is_active=True,
        ).order_by('-importance').first()
        return Response({'name': persona.trait_value if persona else None})

    serializer = UserNameSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    name = serializer.validated_data['name']

    # Deactivate old name records, then create new one
    UserPersona.objects.filter(
        user=user,
        category='identity',
        trait_key='name',
        is_active=True,
    ).update(is_active=False)

    UserPersona.objects.create(
        user=user,
        category='identity',
        trait_key='name',
        trait_value=name,
        importance=9,
        is_active=True,
    )

    return Response({'name': name}, status=status.HTTP_200_OK)


def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('home')
        return render(request, 'chat/login.html', {'error': '아이디나 비밀번호가 틀렸어.'})
    return render(request, 'chat/login.html')


def signup_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        e = request.POST.get('email')
        p = request.POST.get('password')
        pc = request.POST.get('password_confirm')

        if User.objects.filter(username=u).exists():
            return render(request, 'chat/signup.html', {'error': '이미 있는 아이디야. 다른 걸로 해줘!'})
        if p != pc:
            return render(request, 'chat/signup.html', {'error': '비밀번호가 서로 달라. 다시 확인해줘!'})

        User.objects.create_user(username=u, email=e, password=p)
        return redirect('signup_success')
    return render(request, 'chat/signup.html')


def signup_success(request):
    return render(request, 'chat/signup_success.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def health_check(request):
    from django.db import connection
    from django.conf import settings

    db_ok = False
    db_error = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_ok = True
    except Exception as e:
        db_error = str(e)

    return JsonResponse({
        "status": "ok",
        "database_type": settings.DATABASES['default']['ENGINE'],
        "database_connected": db_ok,
        "database_error": db_error,
        "allowed_hosts": settings.ALLOWED_HOSTS,
    })


# ── ADMIN PANEL ────────────────────────────────────────────────────────────────

def admin_dashboard(request):
    if not settings.DEBUG:
        _try_jwt_auth(request)
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect('/')
    AuthUser = get_user_model()
    today = timezone.now().date()
    active_tab = request.GET.get('tab', 'dashboard')
    search_user = request.GET.get('search_user', '')

    def safe(fn, default=0):
        try:
            return fn()
        except Exception:
            return default

    users_qs = safe(lambda: AuthUser.objects.order_by('-date_joined'), [])
    if search_user and users_qs:
        try:
            users_qs = users_qs.filter(username__icontains=search_user)
        except Exception:
            pass

    context = {
        'active_tab': active_tab,
        'search_user': search_user,
        'total_users':        safe(lambda: AuthUser.objects.count()),
        'today_visits':       safe(lambda: VisitLog.objects.filter(visit_time__date=today).count()),
        'total_messages':     safe(lambda: Message.objects.count()),
        'published_contents': safe(lambda: GeneratedContent.objects.filter(is_published=True).count()),
        'total_contents':     safe(lambda: GeneratedContent.objects.count()),
        'total_knowledge':    safe(lambda: HariKnowledge.objects.count()),
        'total_memories':     safe(lambda: ChatMemory.objects.count()),
        'users':              safe(lambda: list(users_qs[:50]), []),
        'recent_users':       safe(lambda: list(AuthUser.objects.order_by('-date_joined')[:8]), []),
        'contents':           safe(lambda: list(GeneratedContent.objects.order_by('-created_at')[:50]), []),
        'hari_knowledge':     safe(lambda: list(HariKnowledge.objects.order_by('-updated_at')), []),
        'recent_messages':    safe(lambda: list(Message.objects.select_related('user').order_by('-created_at')[:8]), []),
        'all_messages':       safe(lambda: list(Message.objects.select_related('user').order_by('-created_at')[:100]), []),
        'chat_memories':      safe(lambda: list(ChatMemory.objects.select_related('user').order_by('-ended_at')[:50]), []),
    }
    return render(request, 'frontend/admin.html', context)


@require_POST
def admin_toggle_content(request, content_id):
    if not settings.DEBUG:
        _try_jwt_auth(request)
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'ok': False}, status=403)
    try:
        content = GeneratedContent.objects.get(content_id=content_id)
        content.is_published = not content.is_published
        content.save()
        return JsonResponse({'ok': True, 'is_published': content.is_published})
    except GeneratedContent.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)


@require_POST
def admin_toggle_knowledge(request, persona_id):
    if not settings.DEBUG:
        _try_jwt_auth(request)
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse({'ok': False}, status=403)
    try:
        k = HariKnowledge.objects.get(persona_id=persona_id)
        k.is_active = not k.is_active
        k.save()
        return JsonResponse({'ok': True, 'is_active': k.is_active})
    except HariKnowledge.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)
