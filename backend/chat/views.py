from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
import os
from rest_framework import viewsets, permissions
from .models import ChatSession, Message
from .serializers import ChatSessionSerializer, MessageSerializer

def chat_index(request):
    if not request.user.is_authenticated and not request.session.session_key:
        request.session.create()
        request.session['init'] = True  # Ensure session is not empty so cookie is sent
    return render(request, 'chat/index.html')

class ChatSessionViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.AllowAny]
    ordering = ['-updated_at']

    def get_queryset(self):
        # We can't use session_key column because it's missing from DB.
        # Fallback tracking using the 'summary' field which is a TextField.
        existing_fields = ['id', 'user_id', 'started_at', 'updated_at', 'summary']
        if self.request.user.is_authenticated:
            return ChatSession.objects.filter(user=self.request.user).only(*existing_fields)
        
        session_key = self.request.session.session_key
        if session_key:
            return ChatSession.objects.filter(user=None, summary=session_key).only(*existing_fields)
        return ChatSession.objects.none()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            if not self.request.session.session_key:
                self.request.session.create()
            # Store session_key in 'summary' field as a workaround
            serializer.save(user=None, summary=self.request.session.session_key)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        # Allow filtering by session ID if provided in query params
        session_id = self.request.query_params.get('session')
        existing_session_fields = ['id', 'user_id', 'started_at', 'updated_at', 'summary']
        
        if session_id:
            try:
                if self.request.user.is_authenticated:
                    latest_session = ChatSession.objects.filter(id=session_id, user=self.request.user).only(*existing_session_fields).first()
                else:
                    session_key = self.request.session.session_key
                    latest_session = ChatSession.objects.filter(id=session_id, user=None, summary=session_key).only(*existing_session_fields).first()
            except:
                latest_session = None
        else:
            # Default to latest session
            if self.request.user.is_authenticated:
                latest_session = ChatSession.objects.filter(user=self.request.user).only(*existing_session_fields).order_by('-updated_at').first()
            else:
                session_key = self.request.session.session_key
                if not session_key:
                    return Message.objects.none()
                latest_session = ChatSession.objects.filter(user=None, summary=session_key).only(*existing_session_fields).order_by('-updated_at').first()
            
        if latest_session:
            return Message.objects.filter(session=latest_session).order_by('created_at')
        return Message.objects.none()

    def perform_create(self, serializer):
        session = serializer.validated_data['session']
        if self.request.user.is_authenticated:
            if session.user == self.request.user:
                serializer.save()
            else:
                raise PermissionError("You do not own this session.")
        else:
            session_key = self.request.session.session_key
            # session_key is stored in summary for guests
            if session.user is None and session.summary == session_key:
                serializer.save()
            else:
                raise PermissionError("Not authorized for this session.")

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'chat/login.html', {'error': '아이디나 비밀번호가 틀렸어. 😢'})
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

def debug_env(request):
    from .engine import engine
    api_key = os.environ.get("OPENAI_API_KEY", "NOT_FOUND")
    # Mask most of the key for security
    masked_key = f"{api_key[:12]}..." if len(api_key) > 12 else api_key
    
    return JsonResponse({
        "OPENAI_API_KEY_LOADED": api_key != "NOT_FOUND",
        "KEY_PREVIEW": masked_key,
        "ENGINE_INITIALIZED": engine.chain is not None,
        "ENGINE_INIT_ERROR": engine.init_error,
        "REDIS_HOST": os.environ.get("REDIS_HOST", "localhost (default)")
    })
