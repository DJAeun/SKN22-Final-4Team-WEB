from datetime import timedelta, date as date_type
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes as perm_classes
from rest_framework.response import Response
from dj_rest_auth.jwt_auth import JWTCookieAuthentication
from .models import Message, ChatMemory, HariKnowledge, GeneratedContent, VisitLog, UserPersona
from .serializers import (
    MessageSerializer, ChatMemorySerializer, UserNameSerializer,
    UserPreferenceSerializer, FrontendSignupSerializer,
)


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
    contents = []
    try:
        # ID 1번(앤트로픽)이 최신이므로 오름차순 정렬
        contents = list(GeneratedContent.objects.filter(is_published=True).order_by('content_id')[:8])
    except Exception:
        pass  # 테이블이 없어도 사이트가 죽지 않도록 예외 처리
    return render(request, 'frontend/homepage.html', {'contents': contents})


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
    _try_jwt_auth(request)
    contents = []
    try:
        # ID 1번(앤트로픽)이 최신이므로 오름차순 정렬
        contents = list(GeneratedContent.objects.filter(is_published=True).order_by('content_id'))
    except Exception:
        pass
    return render(request, 'frontend/video.html', {'contents': contents})


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

    from .memory_extractor import update_user_preference
    update_user_preference(user.id, name=name)

    return Response({'name': name}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@perm_classes([permissions.IsAuthenticated])
def user_preference_view(request):
    """
    GET: return {"tone": "casual"|"formal", "title": str|null} — Hari's speech
    tone and the honorific she uses for the user. Defaults to casual / no title.
    POST: partial update — any subset of {"tone", "title"}. Passing
    title as "" or null clears it.
    """
    user = request.user

    def _current():
        rows = UserPersona.objects.filter(
            user=user,
            category='preference',
            is_active=True,
        ).order_by('-importance')
        tone = 'casual'
        title = None
        for r in rows:
            if r.trait_key == 'tone' and r.trait_value in ('casual', 'formal'):
                tone = r.trait_value
            elif r.trait_key == 'title' and r.trait_value:
                title = r.trait_value
        return {'tone': tone, 'title': title}

    if request.method == 'GET':
        return Response(_current())

    serializer = UserPreferenceSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    from .memory_extractor import update_user_preference
    kwargs = {}
    if 'tone' in data:
        kwargs['tone'] = data['tone']
    if 'title' in data:
        # empty string / None → explicit clear; helper interprets "" as clear
        kwargs['title'] = data['title'] or ''
    update_user_preference(user.id, **kwargs)

    return Response(_current(), status=status.HTTP_200_OK)


@api_view(['POST'])
@perm_classes([permissions.AllowAny])
def frontend_signup_view(request):
    serializer = FrontendSignupSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    AuthUser = get_user_model()
    email = data['email']
    nickname = data['nickname']

    if AuthUser.objects.filter(email__iexact=email).exists():
        return Response(
            {'email': ['이미 가입된 이메일입니다.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if AuthUser.objects.filter(username__iexact=nickname).exists():
        return Response(
            {'username': ['이미 사용 중인 닉네임입니다.']},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = AuthUser.objects.create_user(
        username=nickname,
        email=email,
        password=data['password'],
        first_name=data['name'],
    )

    try:
        from .memory_extractor import update_user_preference
        update_user_preference(user.id, name=data['name'])
    except Exception:
        pass

    return Response(
        {'detail': '회원가입이 완료되었습니다.'},
        status=status.HTTP_201_CREATED,
    )


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
        'contents':           safe(lambda: list(GeneratedContent.objects.order_by('content_id')[:50]), []),
        'hari_knowledge':     safe(lambda: list(HariKnowledge.objects.order_by('-updated_at')), []),
        'recent_messages':    safe(lambda: list(Message.objects.select_related('user').order_by('-created_at')[:8]), []),
        'all_messages':       safe(lambda: list(Message.objects.select_related('user').order_by('-created_at')[:100]), []),
        'chat_memories':      safe(lambda: list(ChatMemory.objects.select_related('user').order_by('-ended_at')[:50]), []),
    }
    return render(request, 'frontend/admin.html', context)


@staff_member_required
def admin_stats_api(request):
    """어드민 대시보드 차트용 JSON API (staff only).

    TruncDay/TruncWeek/TruncMonth/TruncYear + annotate(count=Count('pk'))로
    단일 집계 쿼리를 사용함. 총 쿼리 수 = 3 모델 × 4 기간 = 12회.
    """
    from rpg.models import ChatLog as RpgChatLog
    today = timezone.now().date()

    def safe_qs(qs):
        try:
            return list(qs)
        except Exception:
            return []

    def query_by_period(model, date_field, extra_filter, count_expr=None):
        if count_expr is None:
            count_expr = Count('pk')
        base = model.objects.filter(**extra_filter)

        # DAILY — 최근 7일 (1쿼리)
        day_start = today - timedelta(days=6)
        daily_rows = safe_qs(
            base.filter(**{f'{date_field}__date__gte': day_start})
                .annotate(period=TruncDay(date_field))
                .values('period').annotate(count=count_expr).order_by('period')
        )
        daily_dict = {row['period'].date(): row['count'] for row in daily_rows}
        daily_labels, daily_counts = [], []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily_labels.append(f'{d.month}/{d.day}')
            daily_counts.append(daily_dict.get(d, 0))

        # WEEKLY — 최근 8주 (1쿼리, TruncWeek은 해당 주의 월요일 반환)
        current_mon = today - timedelta(days=today.weekday())
        week_mondays = [current_mon - timedelta(weeks=i) for i in range(7, -1, -1)]
        weekly_rows = safe_qs(
            base.filter(**{f'{date_field}__date__gte': week_mondays[0]})
                .annotate(period=TruncWeek(date_field))
                .values('period').annotate(count=count_expr).order_by('period')
        )
        weekly_dict = {row['period'].date(): row['count'] for row in weekly_rows}
        weekly_labels = [f'W{i + 1}' for i in range(8)]
        weekly_counts = [weekly_dict.get(mon, 0) for mon in week_mondays]

        # MONTHLY — 최근 12개월 (1쿼리)
        m0 = (today.month - 11 - 1) % 12 + 1
        y0 = today.year + (today.month - 11 - 1) // 12
        month_start = date_type(y0, m0, 1)
        monthly_rows = safe_qs(
            base.filter(**{f'{date_field}__date__gte': month_start})
                .annotate(period=TruncMonth(date_field))
                .values('period').annotate(count=count_expr).order_by('period')
        )
        monthly_dict = {(row['period'].year, row['period'].month): row['count'] for row in monthly_rows}
        monthly_labels, monthly_counts = [], []
        for i in range(11, -1, -1):
            m = (today.month - i - 1) % 12 + 1
            y = today.year + (today.month - i - 1) // 12
            monthly_labels.append(f'{m}월')
            monthly_counts.append(monthly_dict.get((y, m), 0))

        # YEARLY — 최근 4년 (1쿼리)
        year_start = date_type(today.year - 3, 1, 1)
        yearly_rows = safe_qs(
            base.filter(**{f'{date_field}__date__gte': year_start})
                .annotate(period=TruncYear(date_field))
                .values('period').annotate(count=count_expr).order_by('period')
        )
        yearly_dict = {row['period'].year: row['count'] for row in yearly_rows}
        yearly_labels = [str(today.year - i) for i in range(3, -1, -1)]
        yearly_counts = [yearly_dict.get(int(y), 0) for y in yearly_labels]

        return {
            'daily':   (daily_labels, daily_counts),
            'weekly':  (weekly_labels, weekly_counts),
            'monthly': (monthly_labels, monthly_counts),
            'yearly':  (yearly_labels, yearly_counts),
        }

    visit_data = query_by_period(VisitLog, 'visit_time', {}, count_expr=Count('user', distinct=True))
    chat_data  = query_by_period(Message,  'created_at', {'sender_type': True})
    rpg_data   = query_by_period(RpgChatLog, 'created_at', {})

    return JsonResponse({
        period: {
            'labels':      visit_data[period][0],
            'visitCounts': visit_data[period][1],
            'chatCounts':  chat_data[period][1],
            'rpgCounts':   rpg_data[period][1],
        }
        for period in ('daily', 'weekly', 'monthly', 'yearly')
    })


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


@require_POST
def contact_form(request):
    name = request.POST.get('contactName', '').strip()
    email = request.POST.get('contactEmail', '').strip()
    company = request.POST.get('contactCompany', '').strip()
    inquiry_type = request.POST.get('contactType', '').strip()
    message = request.POST.get('contactMessage', '').strip()

    if not name or not email or not message:
        return JsonResponse({'ok': False, 'error': '필수 항목을 입력해주세요.'}, status=400)

    subject = f'[Hari 문의] {inquiry_type or "기타"} — {name}'
    body = f"""이름: {name}
이메일: {email}
회사: {company or '-'}
문의 유형: {inquiry_type or '-'}

{message}
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.CONTACT_EMAIL])
        return JsonResponse({'ok': True})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
