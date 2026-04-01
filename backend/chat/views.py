from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from rest_framework import viewsets, permissions
from .models import Message, ChatMemory, HariKnowledge, GeneratedContent, VisitLog
from .serializers import MessageSerializer, ChatMemorySerializer


@ensure_csrf_cookie
def homepage(request):
    return render(request, 'frontend/homepage.html')


def fanpage(request):
    return render(request, 'frontend/fanpage.html')


def frontend_chat(request):
    if not request.user.is_authenticated:
        return redirect('home')
    return render(request, 'frontend/chat.html')


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

@staff_member_required(login_url='/')
def admin_dashboard(request):
    AuthUser = get_user_model()
    today = timezone.now().date()
    active_tab = request.GET.get('tab', 'dashboard')
    search_user = request.GET.get('search_user', '')

    users_qs = AuthUser.objects.order_by('-date_joined')
    if search_user:
        users_qs = users_qs.filter(username__icontains=search_user)

    context = {
        'active_tab': active_tab,
        'search_user': search_user,
        # stats
        'total_users': AuthUser.objects.count(),
        'today_visits': VisitLog.objects.filter(visit_time__date=today).count(),
        'total_messages': Message.objects.count(),
        'published_contents': GeneratedContent.objects.filter(is_published=True).count(),
        'total_contents': GeneratedContent.objects.count(),
        'total_knowledge': HariKnowledge.objects.count(),
        'total_memories': ChatMemory.objects.count(),
        # tables
        'users': users_qs[:50],
        'recent_users': AuthUser.objects.order_by('-date_joined')[:8],
        'contents': GeneratedContent.objects.order_by('-created_at')[:50],
        'hari_knowledge': HariKnowledge.objects.order_by('-updated_at'),
        'recent_messages': Message.objects.select_related('user').order_by('-created_at')[:8],
        'all_messages': Message.objects.select_related('user').order_by('-created_at')[:100],
        'chat_memories': ChatMemory.objects.select_related('user').order_by('-ended_at')[:50],
    }
    return render(request, 'frontend/admin.html', context)


@staff_member_required(login_url='/')
@require_POST
def admin_toggle_content(request, content_id):
    try:
        content = GeneratedContent.objects.get(content_id=content_id)
        content.is_published = not content.is_published
        content.save()
        return JsonResponse({'ok': True, 'is_published': content.is_published})
    except GeneratedContent.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)


@staff_member_required(login_url='/')
@require_POST
def admin_toggle_knowledge(request, persona_id):
    try:
        k = HariKnowledge.objects.get(persona_id=persona_id)
        k.is_active = not k.is_active
        k.save()
        return JsonResponse({'ok': True, 'is_active': k.is_active})
    except HariKnowledge.DoesNotExist:
        return JsonResponse({'ok': False}, status=404)
