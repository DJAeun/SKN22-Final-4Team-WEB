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


@staff_member_required
def youtube_stats_api(request):
    """YouTube Data API v3로 채널 영상 목록과 조회수를 자동으로 반환한다 (staff only).

    흐름:
      1. channels.list → uploads 플레이리스트 ID 획득
      2. playlistItems.list → 최근 영상 ID 목록 획득 (최대 50개)
      3. videos.list → 영상별 통계(조회수·좋아요·댓글) 획득
    """
    import json
    import urllib.request as urlreq
    import urllib.error
    from urllib.parse import urlencode

    api_key = settings.YOUTUBE_API_KEY
    channel_handle = settings.YOUTUBE_CHANNEL_HANDLE

    if not api_key:
        return JsonResponse({'error': 'YOUTUBE_API_KEY not configured'}, status=500)

    def yt_get(endpoint, params):
        params['key'] = api_key
        url = f'https://www.googleapis.com/youtube/v3/{endpoint}?{urlencode(params)}'
        with urlreq.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read())

    try:
        # 1단계: 채널 핸들 → uploads 플레이리스트 ID + 구독자 수
        ch_data = yt_get('channels', {
            'part': 'contentDetails,statistics',
            'forHandle': channel_handle,
        })
        items = ch_data.get('items', [])
        if not items:
            return JsonResponse({'error': f'Channel not found: {channel_handle}'}, status=404)
        uploads_playlist_id = items[0]['contentDetails']['relatedPlaylists']['uploads']
        subscriber_count = int(items[0].get('statistics', {}).get('subscriberCount', 0))

        # 2단계: 플레이리스트 → 영상 ID 목록 (최대 50개)
        pl_data = yt_get('playlistItems', {
            'part': 'contentDetails',
            'playlistId': uploads_playlist_id,
            'maxResults': 50,
        })
        video_ids = [
            item['contentDetails']['videoId']
            for item in pl_data.get('items', [])
        ]
        if not video_ids:
            return JsonResponse({'videos': []})

        # 3단계: 영상 ID → 통계
        stats_data = yt_get('videos', {
            'part': 'statistics,snippet',
            'id': ','.join(video_ids),
        })

    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'YouTube API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    result = []
    for item in stats_data.get('items', []):
        stats = item.get('statistics', {})
        result.append({
            'id':           item['id'],
            'title':        item['snippet']['title'],
            'viewCount':    int(stats.get('viewCount', 0)),
            'likeCount':    int(stats.get('likeCount', 0)),
            'commentCount': int(stats.get('commentCount', 0)),
        })

    result.sort(key=lambda x: x['viewCount'], reverse=True)
    return JsonResponse({'videos': result, 'subscriberCount': subscriber_count})


@staff_member_required
def youtube_oauth_start(request):
    """YouTube Analytics OAuth2 인증 시작 — 구글 로그인 페이지로 리다이렉트."""
    from urllib.parse import urlencode
    if not settings.YOUTUBE_CLIENT_ID:
        return JsonResponse({'error': 'YOUTUBE_CLIENT_ID not configured'}, status=500)
    redirect_uri = request.build_absolute_uri('/admin/youtube-oauth-callback/')
    params = {
        'client_id':     settings.YOUTUBE_CLIENT_ID,
        'redirect_uri':  redirect_uri,
        'response_type': 'code',
        'scope':         'https://www.googleapis.com/auth/yt-analytics.readonly',
        'access_type':   'offline',
        'prompt':        'consent',
    }
    return redirect('https://accounts.google.com/o/oauth2/auth?' + urlencode(params))


@staff_member_required
def youtube_oauth_callback(request):
    """OAuth2 콜백 — 인가 코드를 토큰으로 교환 후 캐시에 저장."""
    import json, time
    import urllib.request as urlreq
    from urllib.parse import urlencode
    from django.core.cache import cache

    if request.GET.get('error') or not request.GET.get('code'):
        return redirect('/admin/?yt_auth=error')

    redirect_uri = request.build_absolute_uri('/admin/youtube-oauth-callback/')
    body = urlencode({
        'code':          request.GET['code'],
        'client_id':     settings.YOUTUBE_CLIENT_ID,
        'client_secret': settings.YOUTUBE_CLIENT_SECRET,
        'redirect_uri':  redirect_uri,
        'grant_type':    'authorization_code',
    }).encode()
    try:
        req = urlreq.Request(
            'https://oauth2.googleapis.com/token', data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST',
        )
        with urlreq.urlopen(req, timeout=10) as resp:
            tokens = json.loads(resp.read())
    except Exception:
        return redirect('/admin/?yt_auth=error')

    tokens['expires_at'] = time.time() + tokens.get('expires_in', 3600)
    cache.set('youtube_oauth_tokens', tokens, 60 * 60 * 24 * 90)  # 90일 보관
    return redirect('/admin/?yt_auth=success')


def _get_yt_access_token():
    """캐시에서 유효한 access_token 반환. 만료 임박 시 refresh_token으로 자동 갱신."""
    import json, time
    import urllib.request as urlreq
    from urllib.parse import urlencode
    from django.core.cache import cache

    tokens = cache.get('youtube_oauth_tokens')
    if not tokens:
        return None

    if time.time() > tokens.get('expires_at', 0) - 300:
        refresh_token = tokens.get('refresh_token')
        if not refresh_token:
            return None
        body = urlencode({
            'client_id':     settings.YOUTUBE_CLIENT_ID,
            'client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'refresh_token': refresh_token,
            'grant_type':    'refresh_token',
        }).encode()
        try:
            req = urlreq.Request(
                'https://oauth2.googleapis.com/token', data=body,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}, method='POST',
            )
            with urlreq.urlopen(req, timeout=10) as resp:
                new_tokens = json.loads(resp.read())
            tokens['access_token'] = new_tokens['access_token']
            tokens['expires_at']   = time.time() + new_tokens.get('expires_in', 3600)
            cache.set('youtube_oauth_tokens', tokens, 60 * 60 * 24 * 90)
        except Exception:
            return None

    return tokens.get('access_token')


@staff_member_required
def youtube_analytics_api(request):
    """YouTube Analytics API — 기간별 채널 조회수·좋아요·댓글 반환 (staff only)."""
    import json
    import urllib.request as urlreq
    import urllib.error
    from urllib.parse import urlencode
    from collections import defaultdict

    access_token = _get_yt_access_token()
    if not access_token:
        return JsonResponse({'error': 'not_authenticated'}, status=401)

    period = request.GET.get('period', 'daily')
    today  = timezone.now().date()

    if period == 'daily':
        start_date = today - timedelta(days=6)
        dimension  = 'day'
    elif period == 'weekly':
        start_date = today - timedelta(weeks=8)
        dimension  = 'day'
    elif period == 'monthly':
        start_date = date_type(today.year - 1, today.month, 1)
        dimension  = 'month'
    else:  # yearly
        start_date = date_type(today.year - 3, 1, 1)
        dimension  = 'month'

    api_url = (
        'https://youtubeanalytics.googleapis.com/v2/reports?'
        + urlencode({
            'ids':       'channel==MINE',
            'startDate': str(start_date),
            'endDate':   str(today),
            'metrics':   'views,likes,comments',
            'dimensions': dimension,
            'sort':       dimension,
        })
    )
    try:
        req = urlreq.Request(api_url, headers={'Authorization': f'Bearer {access_token}'})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'Analytics API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    rows = data.get('rows') or []

    if period == 'daily':
        labels   = [r[0][5:].replace('-', '/') for r in rows]   # YYYY-MM-DD → M/D
        views    = [r[1] for r in rows]
        likes    = [r[2] for r in rows]
        comments = [r[3] for r in rows]

    elif period == 'weekly':
        current_mon = today - timedelta(days=today.weekday())
        week_data   = defaultdict(lambda: [0, 0, 0])
        for r in rows:
            d = date_type(*[int(x) for x in r[0].split('-')])
            wi = (current_mon - d).days // 7   # 0=이번주 … 7=8주전
            if 0 <= wi <= 7:
                week_data[wi][0] += r[1]
                week_data[wi][1] += r[2]
                week_data[wi][2] += r[3]
        labels   = [f'W{i + 1}' for i in range(8)]
        views    = [week_data[7 - i][0] for i in range(8)]
        likes    = [week_data[7 - i][1] for i in range(8)]
        comments = [week_data[7 - i][2] for i in range(8)]

    elif period == 'monthly':
        labels   = [r[0][5:].lstrip('0') + '월' for r in rows]  # YYYY-MM → M월
        views    = [r[1] for r in rows]
        likes    = [r[2] for r in rows]
        comments = [r[3] for r in rows]

    else:  # yearly
        year_data = defaultdict(lambda: [0, 0, 0])
        for r in rows:
            y = r[0][:4]
            year_data[y][0] += r[1]
            year_data[y][1] += r[2]
            year_data[y][2] += r[3]
        years    = sorted(year_data.keys())
        labels   = [y + '년' for y in years]
        views    = [year_data[y][0] for y in years]
        likes    = [year_data[y][1] for y in years]
        comments = [year_data[y][2] for y in years]

    return JsonResponse({'labels': labels, 'views': views, 'likes': likes, 'comments': comments})


@staff_member_required
def youtube_video_analytics_api(request):
    """YouTube Analytics API — 기간별 영상별 조회수 반환 (staff only)."""
    import json
    import urllib.request as urlreq
    import urllib.error
    from urllib.parse import urlencode

    access_token = _get_yt_access_token()
    if not access_token:
        return JsonResponse({'error': 'not_authenticated'}, status=401)

    period = request.GET.get('period', 'daily')
    today  = timezone.now().date()

    if period == 'daily':
        start_date = today - timedelta(days=6)
    elif period == 'weekly':
        start_date = today - timedelta(weeks=8)
    elif period == 'monthly':
        start_date = date_type(today.year - 1, today.month, 1)
    else:
        start_date = date_type(today.year - 3, 1, 1)

    api_url = (
        'https://youtubeanalytics.googleapis.com/v2/reports?'
        + urlencode({
            'ids':        'channel==MINE',
            'startDate':  str(start_date),
            'endDate':    str(today),
            'metrics':    'views,likes,comments',
            'dimensions': 'video',
            'sort':       '-views',
            'maxResults': 50,
        })
    )
    try:
        req = urlreq.Request(api_url, headers={'Authorization': f'Bearer {access_token}'})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'Analytics API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    rows = data.get('rows') or []
    result = [{'id': r[0], 'views': r[1], 'likes': r[2], 'comments': r[3]} for r in rows]
    return JsonResponse({'videos': result})


@staff_member_required
def instagram_stats_api(request):
    """Instagram Graph API — 팔로워 수, 게시물 수 반환 (staff only)."""
    import json
    import urllib.request as urlreq
    import urllib.error

    access_token = getattr(settings, 'INSTAGRAM_ACCESS_TOKEN', '')
    if not access_token:
        return JsonResponse({'error': 'INSTAGRAM_ACCESS_TOKEN not configured'}, status=500)

    try:
        url = (
            'https://graph.instagram.com/v22.0/me'
            '?fields=followers_count,media_count'
            f'&access_token={access_token}'
        )
        with urlreq.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'Instagram API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    return JsonResponse({
        'followers_count': data.get('followers_count', 0),
        'media_count':     data.get('media_count', 0),
    })


@staff_member_required
def instagram_media_api(request):
    """Instagram Graph API — 게시물 목록 + 좋아요/조회수(Insights) 반환 (staff only)."""
    import json
    import urllib.request as urlreq
    import urllib.error
    from concurrent.futures import ThreadPoolExecutor, as_completed

    access_token = getattr(settings, 'INSTAGRAM_ACCESS_TOKEN', '')
    if not access_token:
        return JsonResponse({'error': 'INSTAGRAM_ACCESS_TOKEN not configured'}, status=500)

    try:
        url = (
            'https://graph.instagram.com/v22.0/me/media'
            '?fields=id,caption,media_type,timestamp,like_count,comments_count'
            '&limit=20'
            f'&access_token={access_token}'
        )
        with urlreq.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'Instagram API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    items = data.get('data', [])

    def fetch_views(media_id):
        insights_url = (
            f'https://graph.instagram.com/v22.0/{media_id}/insights'
            f'?metric=views&access_token={access_token}'
        )
        try:
            with urlreq.urlopen(insights_url, timeout=5) as resp:
                d = json.loads(resp.read())
                return media_id, d.get('data', [{}])[0].get('values', [{}])[0].get('value', 0)
        except Exception:
            return media_id, 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_views, item['id']): item['id'] for item in items}
        views_map = {media_id: views for future in as_completed(futures) for media_id, views in [future.result()]}

    media_list = []
    for item in items:
        caption = (item.get('caption') or '').strip().split('\n')[0][:30]
        media_list.append({
            'id':             item.get('id'),
            'caption':        caption or f"게시물 {str(item.get('id', ''))[-6:]}",
            'media_type':     item.get('media_type', 'IMAGE'),
            'timestamp':      item.get('timestamp', ''),
            'like_count':     item.get('like_count', 0),
            'comments_count': item.get('comments_count', 0),
            'views':          views_map.get(item.get('id'), 0),
        })

    return JsonResponse({'media': media_list})


@staff_member_required
def tiktok_oauth_start(request):
    """TikTok OAuth2 인증 시작 — TikTok 로그인 페이지로 리다이렉트."""
    import secrets
    from urllib.parse import urlencode
    if not settings.TIKTOK_CLIENT_KEY:
        return JsonResponse({'error': 'TIKTOK_CLIENT_KEY not configured'}, status=500)
    state = secrets.token_urlsafe(16)
    request.session['tiktok_oauth_state'] = state
    params = {
        'client_key':     settings.TIKTOK_CLIENT_KEY,
        'redirect_uri':   'https://chatting-hari.com/admin/tiktok-oauth-callback/',
        'response_type':  'code',
        'scope':          'user.info.basic,user.info.stats',
        'state':          state,
    }
    return redirect('https://www.tiktok.com/v2/auth/authorize/?' + urlencode(params))


@staff_member_required
def tiktok_oauth_callback(request):
    """TikTok OAuth2 콜백 — 인가 코드를 토큰으로 교환 후 캐시에 저장."""
    import json, time
    import urllib.request as urlreq
    from urllib.parse import urlencode
    from django.core.cache import cache

    if request.GET.get('error') or not request.GET.get('code'):
        return redirect('/admin/?tiktok_auth=error')

    body = urlencode({
        'client_key':     settings.TIKTOK_CLIENT_KEY,
        'client_secret':  settings.TIKTOK_CLIENT_SECRET,
        'code':           request.GET['code'],
        'grant_type':     'authorization_code',
        'redirect_uri':   'https://chatting-hari.com/admin/tiktok-oauth-callback/',
    }).encode()
    try:
        req = urlreq.Request(
            'https://open.tiktokapis.com/v2/oauth/token/',
            data=body,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            method='POST',
        )
        with urlreq.urlopen(req, timeout=10) as resp:
            tokens = json.loads(resp.read())
    except Exception:
        return redirect('/admin/?tiktok_auth=error')

    tokens['expires_at'] = time.time() + tokens.get('expires_in', 86400)
    cache.set('tiktok_oauth_tokens', tokens, 60 * 60 * 24 * 90)
    return redirect('/admin/?tiktok_auth=success')


@staff_member_required
def tiktok_stats_api(request):
    """TikTok API — 팔로워 수, 좋아요 수, 영상 수 반환 (staff only)."""
    import json
    import urllib.request as urlreq
    import urllib.error
    from urllib.parse import urlencode
    from django.core.cache import cache

    tokens = cache.get('tiktok_oauth_tokens')
    if not tokens:
        return JsonResponse({'error': 'not_authenticated'}, status=401)

    access_token = tokens.get('access_token')
    try:
        url = 'https://open.tiktokapis.com/v2/user/info/?fields=follower_count,following_count,likes_count,video_count'
        req = urlreq.Request(url, headers={'Authorization': f'Bearer {access_token}'})
        with urlreq.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return JsonResponse({'error': f'TikTok API error: {e.code}'}, status=502)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    user = data.get('data', {}).get('user', {})
    return JsonResponse({
        'follower_count':  user.get('follower_count', 0),
        'likes_count':     user.get('likes_count', 0),
        'video_count':     user.get('video_count', 0),
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
